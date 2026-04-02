"""거버넌스 정책/컴플라이언스 도메인 모델 — 정책 평가와 승인 워크플로

기존 topic/schema 모듈에 흩어져 있던 정책(naming, guardrail, lint)을
하나의 거버넌스 도메인으로 통합한다.

정책은 Data Product와 Data Contract에 적용되며,
위반 시 승인 워크플로를 통해 예외 처리할 수 있다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.governance.types import (
    ApprovalId,
    ApprovalStatus,
    PolicyId,
    PolicyScope,
    PolicyStatus,
    PolicyType,
    RiskLevel,
    RuleId,
)
from app.shared.exceptions.governance_exceptions import (
    PolicyNotFoundError,
)
from app.shared.types import DomainName, Environment, ProductId

# ============================================================================
# Value Objects
# ============================================================================


@dataclass(frozen=True, slots=True)
class PolicyRule:
    """정책 규칙 — 정책 내 개별 검증 항목"""

    rule_id: RuleId
    name: str
    expression: str
    message: str
    severity: RiskLevel = RiskLevel.MEDIUM

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("policy rule name must not be empty")
        if not self.expression:
            raise ValueError("policy rule must have an expression")


@dataclass(frozen=True, slots=True)
class PolicyViolation:
    """정책 위반 — 평가 결과로 생성되는 불변 기록"""

    rule_id: RuleId
    rule_name: str
    message: str
    severity: RiskLevel
    resource_id: str
    resource_type: str
    details: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class PolicyEvaluation:
    """정책 평가 결과 — 읽기전용 스냅샷"""

    policy_id: PolicyId
    policy_name: str
    target_id: str
    violations: tuple[PolicyViolation, ...]
    evaluated_at: datetime
    score: float

    @property
    def passed(self) -> bool:
        return len(self.violations) == 0

    @property
    def critical_violations(self) -> list[PolicyViolation]:
        return [v for v in self.violations if v.severity is RiskLevel.CRITICAL]

    @property
    def has_critical(self) -> bool:
        return any(v.severity is RiskLevel.CRITICAL for v in self.violations)


# ============================================================================
# Aggregate Root — Policy
# ============================================================================


@dataclass(slots=True)
class GovernancePolicy:
    """거버넌스 정책 — 규칙 묶음과 적용 범위를 정의

    Aggregate Root. 상태 전이(draft → active → archived)가 있으므로
    frozen이 아닌 가변 dataclass.
    """

    policy_id: PolicyId
    name: str
    description: str
    policy_type: PolicyType
    status: PolicyStatus
    scope: PolicyScope

    # 정책 규칙 (1:N)
    rules: list[PolicyRule] = field(default_factory=list)

    # 적용 대상 필터
    target_domains: list[DomainName] = field(default_factory=list)
    target_environments: list[Environment] = field(default_factory=list)
    target_products: list[ProductId] = field(default_factory=list)

    # 버전 관리
    version: int = 1
    content: dict[str, Any] = field(default_factory=dict)

    # 감사
    created_by: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None
    activated_at: datetime | None = None

    # ------------------------------------------------------------------ #
    # 불변 조건
    # ------------------------------------------------------------------ #

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("policy name must not be empty")

    # ------------------------------------------------------------------ #
    # 상태 전이
    # ------------------------------------------------------------------ #

    def activate(self) -> None:
        """DRAFT → ACTIVE"""
        if self.status is not PolicyStatus.DRAFT:
            raise ValueError(f"can only activate from draft, current: {self.status}")
        if not self.rules:
            raise ValueError("cannot activate policy without rules")
        self.status = PolicyStatus.ACTIVE
        self.activated_at = datetime.now()

    def archive(self) -> None:
        """ACTIVE → ARCHIVED"""
        if self.status is not PolicyStatus.ACTIVE:
            raise ValueError(f"can only archive from active, current: {self.status}")
        self.status = PolicyStatus.ARCHIVED

    def new_version(self) -> None:
        """새 버전 생성 (ARCHIVED → DRAFT clone)"""
        self.version += 1
        self.status = PolicyStatus.DRAFT
        self.activated_at = None

    # ------------------------------------------------------------------ #
    # 규칙 관리
    # ------------------------------------------------------------------ #

    def add_rule(self, rule: PolicyRule) -> None:
        if self.status is not PolicyStatus.DRAFT:
            raise ValueError("can only modify rules in draft status")
        for existing in self.rules:
            if existing.rule_id == rule.rule_id:
                raise ValueError(f"duplicate rule: {rule.rule_id}")
        self.rules.append(rule)

    def remove_rule(self, rule_id: RuleId) -> None:
        if self.status is not PolicyStatus.DRAFT:
            raise ValueError("can only modify rules in draft status")
        original = len(self.rules)
        self.rules = [r for r in self.rules if r.rule_id != rule_id]
        if len(self.rules) == original:
            raise PolicyNotFoundError(rule_id)

    # ------------------------------------------------------------------ #
    # 적용 대상 검사
    # ------------------------------------------------------------------ #

    def applies_to(
        self,
        *,
        domain: DomainName | None = None,
        environment: Environment | None = None,
        product_id: ProductId | None = None,
    ) -> bool:
        """이 정책이 주어진 대상에 적용되는지 검사"""
        if self.status is not PolicyStatus.ACTIVE:
            return False

        if self.scope is PolicyScope.GLOBAL:
            return True

        return not (
            (domain and self.target_domains and domain not in self.target_domains)
            or (
                environment
                and self.target_environments
                and environment not in self.target_environments
            )
            or (product_id and self.target_products and product_id not in self.target_products)
        )


# ============================================================================
# Aggregate Root — ApprovalRequest
# ============================================================================


@dataclass(slots=True)
class ApprovalRequest:
    """승인 요청 — 정책 위반 시 생성되는 예외 처리 워크플로

    Aggregate Root. 상태 전이(pending → approved/rejected/expired)가 있다.
    """

    approval_id: ApprovalId
    resource_type: str
    resource_id: str
    change_type: str
    summary: str
    justification: str
    requested_by: str
    status: ApprovalStatus

    # 위반 근거
    violations: list[PolicyViolation] = field(default_factory=list)
    risk_level: RiskLevel = RiskLevel.MEDIUM

    # 결정 정보
    approver: str | None = None
    decision_reason: str | None = None
    metadata_json: dict[str, Any] = field(default_factory=dict)

    # 타임스탬프
    requested_at: datetime | None = None
    decided_at: datetime | None = None
    expires_at: datetime | None = None

    # ------------------------------------------------------------------ #
    # 상태 전이
    # ------------------------------------------------------------------ #

    def approve(self, approver: str, reason: str) -> None:
        if self.status is not ApprovalStatus.PENDING:
            raise ValueError(f"cannot approve in {self.status} state")
        self.status = ApprovalStatus.APPROVED
        self.approver = approver
        self.decision_reason = reason
        self.decided_at = datetime.now()

    def reject(self, approver: str, reason: str) -> None:
        if self.status is not ApprovalStatus.PENDING:
            raise ValueError(f"cannot reject in {self.status} state")
        self.status = ApprovalStatus.REJECTED
        self.approver = approver
        self.decision_reason = reason
        self.decided_at = datetime.now()

    def expire(self) -> None:
        if self.status is not ApprovalStatus.PENDING:
            raise ValueError(f"cannot expire in {self.status} state")
        self.status = ApprovalStatus.EXPIRED

    # ------------------------------------------------------------------ #
    # 쿼리
    # ------------------------------------------------------------------ #

    @property
    def is_pending(self) -> bool:
        return self.status is ApprovalStatus.PENDING

    @property
    def is_decided(self) -> bool:
        return self.status in (ApprovalStatus.APPROVED, ApprovalStatus.REJECTED)

    @property
    def is_approved(self) -> bool:
        return self.status is ApprovalStatus.APPROVED
