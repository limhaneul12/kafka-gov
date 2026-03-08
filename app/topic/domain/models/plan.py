"""Topic Plan Models"""

from __future__ import annotations

from dataclasses import dataclass

from app.shared.domain.policy_types import DomainPolicySeverity, DomainPolicyViolation
from app.shared.domain.preflight_policy import DomainPolicyPackEvaluation

from .types_enum import ChangeId, DomainEnvironment, DomainPlanAction, TopicName


@dataclass(frozen=True, slots=True)
class DomainTopicPlanItem:
    """토픽 계획 아이템 - Value Object (immutable)"""

    name: TopicName
    action: DomainPlanAction
    diff: dict[str, str]
    current_config: dict[str, str] | None = None
    target_config: dict[str, str] | None = None
    reason: str | None = None

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("name is required")


@dataclass(frozen=True, slots=True)
class DomainTopicPlan:
    """토픽 계획 - Aggregate (immutable)"""

    change_id: ChangeId
    env: DomainEnvironment
    items: tuple[DomainTopicPlanItem, ...]
    violations: tuple[DomainPolicyViolation, ...]
    risk: dict[str, str | bool] | None = None
    approval: dict[str, str | bool] | None = None
    policy_evaluation: DomainPolicyPackEvaluation | None = None
    requested_total: int | None = None
    actor_context: dict[str, str] | None = None

    def __post_init__(self) -> None:
        if not self.change_id:
            raise ValueError("change_id is required")

    @property
    def has_violations(self) -> bool:
        """위반 사항 존재 여부"""
        return len(self.violations) > 0

    @property
    def error_violations(self) -> tuple[DomainPolicyViolation, ...]:
        """에러 수준 위반 사항"""
        return tuple(
            v
            for v in self.violations
            if v.severity in (DomainPolicySeverity.ERROR, DomainPolicySeverity.CRITICAL)
        )

    @property
    def warning_violations(self) -> tuple[DomainPolicyViolation, ...]:
        """경고 수준 위반 사항"""
        return tuple(v for v in self.violations if v.severity == DomainPolicySeverity.WARNING)

    @property
    def can_apply(self) -> bool:
        """적용 가능 여부 (에러 위반이 없는 경우)"""
        return len(self.error_violations) == 0

    @property
    def planned_total(self) -> int:
        return len(self.items)

    @property
    def total_items(self) -> int:
        if self.requested_total is not None:
            return self.requested_total
        return self.planned_total

    @property
    def unchanged_count(self) -> int:
        return max(self.total_items - self.planned_total, 0)

    @property
    def warning_count(self) -> int:
        if self.policy_evaluation is not None:
            return self.policy_evaluation.warning_count
        return len(self.warning_violations)

    def summary(self) -> dict[str, int]:
        """계획 요약"""
        action_counts = {}
        for item in self.items:
            action_counts[item.action.value.lower() + "_count"] = (
                action_counts.get(item.action.value.lower() + "_count", 0) + 1
            )

        return {
            "total_items": self.total_items,
            "planned_count": self.planned_total,
            "create_count": action_counts.get("create_count", 0),
            "alter_count": action_counts.get("alter_count", 0),
            "delete_count": action_counts.get("delete_count", 0),
            "unchanged_count": self.unchanged_count,
            "violation_count": len(self.violations),
            "warning_count": self.warning_count,
        }


@dataclass(frozen=True, slots=True)
class DomainTopicApplyResult:
    """토픽 적용 결과 - Value Object (immutable)"""

    change_id: ChangeId
    env: DomainEnvironment
    applied: tuple[TopicName, ...]
    skipped: tuple[TopicName, ...]
    failed: tuple[dict[str, str], ...]
    audit_id: str
    risk: dict[str, str | bool] | None = None
    approval: dict[str, str | bool] | None = None
    policy_evaluation: DomainPolicyPackEvaluation | None = None
    requested_total: int | None = None
    planned_total: int | None = None
    warning_total: int | None = None
    details: tuple[dict[str, str | None], ...] = ()
    actor_context: dict[str, str] | None = None

    def __post_init__(self) -> None:
        if not self.change_id:
            raise ValueError("change_id is required")
        if not self.audit_id:
            raise ValueError("audit_id is required")

    def summary(self) -> dict[str, int]:
        """적용 결과 요약"""
        total_items = (
            self.requested_total
            if self.requested_total is not None
            else len(self.applied) + len(self.skipped) + len(self.failed)
        )
        planned_total = (
            self.planned_total
            if self.planned_total is not None
            else max(total_items - len(self.skipped), 0)
        )
        unchanged_count = max(total_items - planned_total, 0)
        warning_count = (
            self.warning_total
            if self.warning_total is not None
            else self.policy_evaluation.warning_count
            if self.policy_evaluation is not None
            else 0
        )
        return {
            "total_items": total_items,
            "planned_count": planned_total,
            "applied_count": len(self.applied),
            "skipped_count": unchanged_count,
            "failed_count": len(self.failed),
            "warning_count": warning_count,
        }
