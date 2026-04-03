"""거버넌스 Command — 도메인 의도를 표현하는 불변 스키마"""

from __future__ import annotations

from dataclasses import dataclass

from app.governance.domain.models.governance import PolicyViolation
from app.governance.types import ApprovalId, RiskLevel
from app.shared.types import DomainName, Environment, ProductId


@dataclass(frozen=True, slots=True)
class EvaluatePolicyCommand:
    """정책 평가 요청"""

    target_id: str
    target_type: str
    domain: DomainName | None = None
    environment: Environment | None = None
    product_id: ProductId | None = None
    context: dict[str, str] | None = None


@dataclass(frozen=True, slots=True)
class RequestApprovalCommand:
    """승인 요청 생성"""

    resource_type: str
    resource_id: str
    change_type: str
    summary: str
    justification: str
    requested_by: str
    violations: list[PolicyViolation]
    risk_level: RiskLevel = RiskLevel.MEDIUM
    ttl_hours: int = 72


@dataclass(frozen=True, slots=True)
class DecideApprovalCommand:
    """승인 결정"""

    approval_id: ApprovalId
    approver: str
    reason: str
