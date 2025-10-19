"""Schema Plan and Result Models"""

from __future__ import annotations

from dataclasses import dataclass

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


@dataclass(frozen=True, slots=True)
class DomainSchemaPlan:
    """스키마 배치 계획 - Aggregate"""

    change_id: ChangeId
    env: DomainEnvironment
    items: tuple[DomainSchemaPlanItem, ...]
    violations: tuple[DomainPolicyViolation, ...] = ()
    compatibility_reports: tuple[DomainSchemaCompatibilityReport, ...] = ()
    impacts: tuple[DomainSchemaImpactRecord, ...] = ()

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
            "total_items": len(self.items),
            "register_count": action_counts[DomainPlanAction.REGISTER],
            "update_count": action_counts[DomainPlanAction.UPDATE],
            "delete_count": action_counts[DomainPlanAction.DELETE],
            "none_count": action_counts[DomainPlanAction.NONE],
            "violation_count": len(self.violations),
            "incompatible_count": sum(
                1 for report in self.compatibility_reports if not report.is_compatible
            ),
        }

    @property
    def can_apply(self) -> bool:
        return not any(v.is_error for v in self.violations) and all(
            report.is_compatible for report in self.compatibility_reports
        )

    @property
    def error_violations(self) -> tuple[DomainPolicyViolation, ...]:
        return tuple(v for v in self.violations if v.is_error)


@dataclass(frozen=True, slots=True)
class DomainSchemaArtifact:
    """저장된 스키마 아티팩트 - Value Object"""

    subject: SubjectName
    storage_url: str
    version: int | None = None
    checksum: SchemaHash | None = None
    schema_type: DomainSchemaType | None = None
    compatibility_mode: DomainCompatibilityMode | None = None
    owner: str | None = None

    def __post_init__(self) -> None:
        if self.version is not None and self.version < 1:
            raise ValueError("artifact version must be >= 1")
        if not self.storage_url:
            raise ValueError("storage_url is required")


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

    def summary(self) -> dict[str, int]:
        return {
            "total_items": len(self.registered) + len(self.skipped) + len(self.failed),
            "registered_count": len(self.registered),
            "skipped_count": len(self.skipped),
            "failed_count": len(self.failed),
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
