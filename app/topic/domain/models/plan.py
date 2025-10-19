"""Topic Plan Models"""

from __future__ import annotations

from dataclasses import dataclass

from app.shared.domain.policy_types import DomainPolicySeverity, DomainPolicyViolation

from .types_enum import ChangeId, DomainEnvironment, DomainPlanAction, TopicName


@dataclass(frozen=True, slots=True)
class DomainTopicPlanItem:
    """토픽 계획 아이템 - Value Object (immutable)"""

    name: TopicName
    action: DomainPlanAction
    diff: dict[str, str]
    current_config: dict[str, str] | None = None
    target_config: dict[str, str] | None = None

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

    def summary(self) -> dict[str, int]:
        """계획 요약"""
        action_counts = {}
        for item in self.items:
            action_counts[item.action.value.lower() + "_count"] = (
                action_counts.get(item.action.value.lower() + "_count", 0) + 1
            )

        return {
            "total_items": len(self.items),
            "create_count": action_counts.get("create_count", 0),
            "alter_count": action_counts.get("alter_count", 0),
            "delete_count": action_counts.get("delete_count", 0),
            "violation_count": len(self.violations),
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

    def __post_init__(self) -> None:
        if not self.change_id:
            raise ValueError("change_id is required")
        if not self.audit_id:
            raise ValueError("audit_id is required")

    def summary(self) -> dict[str, int]:
        """적용 결과 요약"""
        return {
            "total_items": len(self.applied) + len(self.skipped) + len(self.failed),
            "applied_count": len(self.applied),
            "skipped_count": len(self.skipped),
            "failed_count": len(self.failed),
        }
