"""Schema Plan and Result Models"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.schema.governance_support.preflight_policy import DomainPolicyPackEvaluation

from .policy import DomainPolicyViolation, DomainSchemaCompatibilityReport, DomainSchemaImpactRecord
from .types_enum import (
    ChangeId,
    DomainCompatibilityMode,
    DomainEnvironment,
    DomainPlanAction,
    DomainSchemaType,
    SchemaHash,
    SubjectName,
)


@dataclass(frozen=True, slots=True)
class DomainSchemaDiff:
    """스키마 변경 사항 - Value Object"""

    type: str  # "new_registration" | "update"
    changes: tuple[str, ...]
    current_version: int | None
    target_compatibility: str
    schema_type: str | None


@dataclass(frozen=True, slots=True)
class DomainSchemaPlanItem:
    """스키마 배치 계획 항목 - Value Object"""

    subject: SubjectName
    action: DomainPlanAction
    current_version: int | None
    target_version: int | None
    diff: DomainSchemaDiff
    schema: str | None = None  # New schema
    current_schema: str | None = None  # Current schema for diff
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class DomainSchemaPlan:
    """스키마 배치 계획 - Aggregate"""

    change_id: ChangeId
    env: DomainEnvironment
    items: tuple[DomainSchemaPlanItem, ...]
    compatibility_reports: tuple[DomainSchemaCompatibilityReport, ...] = ()
    impacts: tuple[DomainSchemaImpactRecord, ...] = ()
    violations: tuple[DomainPolicyViolation, ...] = ()
    risk: dict[str, str | bool] | None = None
    approval: dict[str, str | bool] | None = None
    policy_evaluation: DomainPolicyPackEvaluation | None = None
    requested_total: int | None = None
    actor_context: dict[str, str] | None = None

    @property
    def planned_total(self) -> int:
        return sum(1 for item in self.items if item.action is not DomainPlanAction.NONE)

    @property
    def total_items(self) -> int:
        if self.requested_total is not None:
            return self.requested_total
        return len(self.items)

    @property
    def unchanged_count(self) -> int:
        if self.requested_total is not None:
            return max(self.total_items - self.planned_total, 0)
        return sum(1 for item in self.items if item.action is DomainPlanAction.NONE)

    @property
    def warning_count(self) -> int:
        if self.policy_evaluation is not None:
            return self.policy_evaluation.warning_count
        return sum(1 for violation in self.violations if not violation.is_error)

    def summary(self) -> dict[str, int]:
        """계획 요약 정보"""
        action_counts: dict[DomainPlanAction, int] = {
            DomainPlanAction.REGISTER: 0,
            DomainPlanAction.UPDATE: 0,
            DomainPlanAction.DELETE: 0,
            DomainPlanAction.NONE: 0,
        }
        for item in self.items:
            action_counts[item.action] = action_counts.get(item.action, 0) + 1

        return {
            "total_items": self.total_items,
            "planned_count": self.planned_total,
            "register_count": action_counts[DomainPlanAction.REGISTER],
            "update_count": action_counts[DomainPlanAction.UPDATE],
            "delete_count": action_counts[DomainPlanAction.DELETE],
            "none_count": self.unchanged_count,
            "incompatible_count": sum(
                1 for report in self.compatibility_reports if not report.is_compatible
            ),
            "violation_count": len(self.violations),
            "warning_count": self.warning_count,
        }

    @property
    def can_apply(self) -> bool:
        """적용 가능 여부 - 호환성 문제가 없고, Error 등급 위반이 없어야 함"""
        if not all(report.is_compatible for report in self.compatibility_reports):
            return False

        return not any(v.is_error for v in self.violations)


@dataclass(frozen=True, slots=True)
class DomainSchemaArtifact:
    """저장된 스키마 아티팩트 - Value Object"""

    subject: SubjectName
    storage_url: str | None  # Optional when no Object Storage
    version: int | None = None
    checksum: SchemaHash | None = None
    schema_type: DomainSchemaType | None = None
    compatibility_mode: DomainCompatibilityMode | None = None
    owner: str | None = None
    created_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.version is not None and self.version < 1:
            raise ValueError("artifact version must be >= 1")


@dataclass(frozen=True, slots=True)
class DomainSchemaApplyResult:
    """스키마 배치 적용 결과 - Value Object"""

    change_id: ChangeId
    env: DomainEnvironment
    registered: tuple[SubjectName, ...]
    skipped: tuple[SubjectName, ...]
    failed: tuple[dict[str, str], ...]
    audit_id: str
    artifacts: tuple[DomainSchemaArtifact, ...] = ()
    risk: dict[str, str | bool] | None = None
    approval: dict[str, str | bool] | None = None
    policy_evaluation: DomainPolicyPackEvaluation | None = None
    requested_total: int | None = None
    planned_total: int | None = None
    warning_total: int | None = None
    details: tuple[dict[str, str | None], ...] = ()
    actor_context: dict[str, str] | None = None

    def summary(self) -> dict[str, int]:
        total_items = (
            self.requested_total
            if self.requested_total is not None
            else len(self.registered) + len(self.skipped) + len(self.failed)
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
            "registered_count": len(self.registered),
            "skipped_count": unchanged_count,
            "failed_count": len(self.failed),
            "warning_count": warning_count,
        }


@dataclass(frozen=True, slots=True)
class DomainSchemaUploadResult:
    """스키마 업로드 결과 - Value Object"""

    upload_id: str
    artifacts: tuple[DomainSchemaArtifact, ...]

    def summary(self) -> dict[str, int]:
        counts = {
            "total_files": len(self.artifacts),
            "avro_count": 0,
            "json_count": 0,
            "proto_count": 0,
        }
        for artifact in self.artifacts:
            subject_lower = artifact.subject.lower()
            if subject_lower.endswith(".avro"):
                counts["avro_count"] += 1
            elif subject_lower.endswith(".json"):
                counts["json_count"] += 1
            elif subject_lower.endswith(".proto"):
                counts["proto_count"] += 1
        return counts
