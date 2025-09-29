"""Schema Domain 모델 - 불변 도메인 엔티티 및 값 객체"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum
from typing import TypeAlias


class DomainEnvironment(str, Enum):
    """배포 환경"""

    DEV = "dev"
    STG = "stg"
    PROD = "prod"


class DomainSchemaType(str, Enum):
    """Schema Registry 지원 스키마 타입"""

    AVRO = "AVRO"
    JSON = "JSON"
    PROTOBUF = "PROTOBUF"


class DomainCompatibilityMode(str, Enum):
    """스키마 호환성 모드"""

    NONE = "NONE"
    BACKWARD = "BACKWARD"
    BACKWARD_TRANSITIVE = "BACKWARD_TRANSITIVE"
    FORWARD = "FORWARD"
    FORWARD_TRANSITIVE = "FORWARD_TRANSITIVE"
    FULL = "FULL"
    FULL_TRANSITIVE = "FULL_TRANSITIVE"


class DomainSubjectStrategy(str, Enum):
    """스키마 주제 전략"""

    TOPIC_NAME = "TopicNameStrategy"
    RECORD_NAME = "RecordNameStrategy"
    TOPIC_RECORD_NAME = "TopicRecordNameStrategy"


class DomainSchemaSourceType(str, Enum):
    """스키마 소스 타입"""

    INLINE = "inline"
    FILE = "file"
    YAML = "yaml"


class DomainPlanAction(str, Enum):
    """배치 계획 액션"""

    REGISTER = "REGISTER"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    NONE = "NONE"


# 타입 별칭
SubjectName: TypeAlias = str
ChangeId: TypeAlias = str
SchemaDefinition: TypeAlias = str
SchemaYamlText: TypeAlias = str
FileReference: TypeAlias = str
ReasonText: TypeAlias = str
SchemaHash: TypeAlias = str
Actor: TypeAlias = str


@dataclass(slots=True, frozen=True)
class DomainSchemaMetadata:
    """스키마 메타데이터 값 객체"""

    owner: str
    doc: str | None = None
    tags: tuple[str, ...] = ()
    description: str | None = None

    def __post_init__(self) -> None:
        if not self.owner:
            raise ValueError("owner is required")


@dataclass(slots=True, frozen=True)
class DomainSchemaReference:
    """스키마 참조 정보"""

    name: str
    subject: SubjectName
    version: int

    def __post_init__(self) -> None:
        if self.version < 1:
            raise ValueError("reference version must be >= 1")
        if not self.name:
            raise ValueError("reference name is required")
        if not self.subject:
            raise ValueError("reference subject is required")


@dataclass(slots=True, frozen=True)
class DomainSchemaSource:
    """스키마 소스 정의"""

    type: DomainSchemaSourceType
    inline: SchemaDefinition | None = None
    file: FileReference | None = None
    yaml: SchemaYamlText | None = None

    def __post_init__(self) -> None:
        if self.type is DomainSchemaSourceType.INLINE:
            if not self.inline:
                raise ValueError("inline source requires inline content")
            if self.file or self.yaml:
                raise ValueError("inline source cannot include file or yaml data")
        elif self.type is DomainSchemaSourceType.FILE:
            if not self.file:
                raise ValueError("file source requires file reference")
            if self.inline or self.yaml:
                raise ValueError("file source cannot include inline or yaml data")
        elif self.type is DomainSchemaSourceType.YAML:
            if not self.yaml:
                raise ValueError("yaml source requires yaml content")
            if self.inline or self.file:
                raise ValueError("yaml source cannot include inline or file data")


@dataclass(slots=True, frozen=True)
class DomainSchemaSpec:
    """스키마 등록 명세"""

    subject: SubjectName
    schema_type: DomainSchemaType
    compatibility: DomainCompatibilityMode
    schema: SchemaDefinition | None = None
    source: DomainSchemaSource | None = None
    schema_hash: SchemaHash | None = None
    references: tuple[DomainSchemaReference, ...] = ()
    metadata: DomainSchemaMetadata | None = None
    reason: ReasonText | None = None
    dry_run_only: bool = False

    def __post_init__(self) -> None:
        if not self.subject:
            raise ValueError("subject is required")

        if not (self.schema or self.source):
            raise ValueError("schema spec must provide schema or source")

        if self.schema and self.source and self.source.type is not DomainSchemaSourceType.INLINE:
            raise ValueError("schema literal is only allowed when source is inline or omitted")

    @property
    def environment(self) -> DomainEnvironment:
        """subject 접두사로부터 환경을 추론"""
        env_prefix = self.subject.split(".")[0]
        return DomainEnvironment(env_prefix)

    def fingerprint(self) -> SchemaHash:
        """스키마 명세 지문 생성"""
        content = f"{self.subject}:{self.schema_type}:{self.compatibility}"
        if self.schema:
            content += f":{self.schema}"
        if self.source:
            content += f":source:{self.source.type}:{self.source.inline or self.source.file or self.source.yaml}"
        if self.references:
            ref_digest = ",".join(
                f"{ref.name}:{ref.subject}:{ref.version}"
                for ref in sorted(self.references, key=lambda r: r.name)
            )
            content += f":refs:{ref_digest}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]


@dataclass(slots=True, frozen=True)
class DomainSchemaBatch:
    """스키마 배치 엔티티"""

    change_id: ChangeId
    env: DomainEnvironment
    subject_strategy: DomainSubjectStrategy
    specs: tuple[DomainSchemaSpec, ...]

    def __post_init__(self) -> None:
        if not self.change_id:
            raise ValueError("change_id is required")
        if not self.specs:
            raise ValueError("specs cannot be empty")

        subjects = [spec.subject for spec in self.specs]
        duplicates = {subject for subject in subjects if subjects.count(subject) > 1}
        if duplicates:
            raise ValueError(f"duplicate subjects detected: {sorted(duplicates)}")

        for spec in self.specs:
            if spec.environment != self.env:
                raise ValueError(
                    f"spec environment {spec.environment.value} does not match batch environment {self.env.value}"
                )

    def fingerprint(self) -> SchemaHash:
        """배치 지문 생성"""
        spec_fingerprints = sorted(spec.fingerprint() for spec in self.specs)
        content = f"{self.change_id}:{self.env.value}:{self.subject_strategy.value}:{':'.join(spec_fingerprints)}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]


@dataclass(slots=True, frozen=True)
class DomainPolicyViolation:
    """정책 위반 정보"""

    subject: SubjectName
    rule: str
    message: str
    severity: str = "error"
    field: str | None = None

    @property
    def is_error(self) -> bool:
        return self.severity == "error"


@dataclass(slots=True, frozen=True)
class DomainSchemaCompatibilityIssue:
    """호환성 위반 상세"""

    path: str
    message: str
    issue_type: str


@dataclass(slots=True, frozen=True)
class DomainSchemaCompatibilityReport:
    """호환성 검증 결과"""

    subject: SubjectName
    mode: DomainCompatibilityMode
    is_compatible: bool
    issues: tuple[DomainSchemaCompatibilityIssue, ...] = ()


@dataclass(slots=True, frozen=True)
class DomainSchemaImpactRecord:
    """스키마 영향도 정보"""

    subject: SubjectName
    topics: tuple[str, ...] = ()
    consumers: tuple[str, ...] = ()


@dataclass(slots=True, frozen=True)
class DomainSchemaPlanItem:
    """스키마 배치 계획 항목"""

    subject: SubjectName
    action: DomainPlanAction
    current_version: int | None
    target_version: int | None
    diff: dict[str, object]


@dataclass(slots=True, frozen=True)
class DomainSchemaPlan:
    """스키마 배치 계획"""

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


@dataclass(slots=True, frozen=True)
class DomainSchemaApplyResult:
    """스키마 배치 적용 결과"""

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


@dataclass(slots=True, frozen=True)
class DomainSchemaArtifact:
    """저장된 스키마 아티팩트"""

    subject: SubjectName
    version: int
    storage_url: str
    checksum: SchemaHash | None = None

    def __post_init__(self) -> None:
        if self.version < 1:
            raise ValueError("artifact version must be >= 1")
        if not self.storage_url:
            raise ValueError("storage_url is required")


@dataclass(slots=True, frozen=True)
class DomainSchemaUploadResult:
    """스키마 업로드 결과"""

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


def ensure_unique_subjects(subjects: Iterable[SubjectName]) -> None:
    """subject 중복 검증"""
    subject_list = list(subjects)
    duplicates = {subject for subject in subject_list if subject_list.count(subject) > 1}
    if duplicates:
        raise ValueError(f"duplicate subjects detected: {sorted(duplicates)}")
