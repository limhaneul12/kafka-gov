"""Schema Interface 스키마 - Pydantic v2 기반 DTO 및 검증 로직"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Annotated, Any

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StrictStr,
    field_validator,
    model_validator,
)

from .types.enums import (
    CompatibilityMode,
    Environment,
    SchemaSourceType,
    SchemaType,
    SubjectStrategy,
)
from .types.type_hints import (
    AuditId,
    ChangeId,
    DocumentUrl,
    ErrorField,
    ErrorMessage,
    ErrorRule,
    ErrorSeverity,
    FileReference,
    PlanAction,
    ReasonText,
    ReferenceName,
    ReferenceSubject,
    SchemaDefinition,
    SchemaHash,
    SchemaVersion,
    SchemaYamlText,
    StorageUrl,
    SubjectName,
    TagName,
    TeamName,
)


class SchemaMetadata(BaseModel):
    """스키마 메타데이터 정보"""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        str_min_length=1,
        str_strip_whitespace=True,
        json_schema_extra={
            "example": {
                "owner": "team-data-platform",
                "doc": "https://wiki.company.com/schemas/order",
                "tags": ["pii", "critical"],
                "description": "주문 이벤트 스키마",
            }
        },
    )

    owner: TeamName
    doc: DocumentUrl | None = None
    tags: list[TagName] = Field(default_factory=list, max_length=15)
    description: StrictStr | None = Field(default=None, max_length=300, description="스키마 설명")


class SchemaReference(BaseModel):
    """스키마 참조 정보"""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        str_min_length=1,
        str_strip_whitespace=True,
        json_schema_extra={
            "example": {
                "name": "common.Address",
                "subject": "prod.common.address-value",
                "version": 5,
            }
        },
    )

    name: ReferenceName
    subject: ReferenceSubject
    version: SchemaVersion


class SchemaSource(BaseModel):
    """스키마 소스 정의"""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        str_min_length=1,
        str_strip_whitespace=True,
        json_schema_extra={
            "example": {
                "type": "inline",
                "inline": '{"type":"record","name":"Order","fields":[...]}',
            }
        },
    )

    type: SchemaSourceType
    inline: SchemaDefinition | None = Field(
        default=None, description="inline 타입일 때의 스키마 본문"
    )
    file: FileReference | None = Field(
        default=None, description="사전 업로드된 파일 경로 또는 스토리지 키"
    )
    yaml: SchemaYamlText | None = Field(default=None, description="YAML 타입일 때 사용되는 정의")

    @model_validator(mode="after")
    def validate_payload(self) -> SchemaSource:
        """소스 타입에 따른 필수 필드 검증"""
        if self.type is SchemaSourceType.INLINE:
            if not self.inline:
                raise ValueError("inline source requires 'inline' content")
            if self.file or self.yaml:
                raise ValueError("inline source cannot include file or yaml data")
        elif self.type is SchemaSourceType.FILE:
            if not self.file:
                raise ValueError("file source requires 'file' reference")
            if self.inline or self.yaml:
                raise ValueError("file source cannot include inline or yaml data")
        elif self.type is SchemaSourceType.YAML:
            if not self.yaml:
                raise ValueError("yaml source requires 'yaml' content")
            if self.inline or self.file:
                raise ValueError("yaml source cannot include inline or file data")
        return self


class SchemaBatchItem(BaseModel):
    """스키마 배치 단일 항목"""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        str_min_length=1,
        str_strip_whitespace=True,
        json_schema_extra={
            "example": {
                "subject": "prod.orders.created-value",
                "type": "AVRO",
                "compatibility": "FULL",
                "schema": '{"type":"record","name":"Order","fields":[{"name":"id","type":"string"}]}',
                "references": [
                    {
                        "name": "common.Address",
                        "subject": "prod.common.address-value",
                        "version": 5,
                    }
                ],
                "metadata": {
                    "owner": "team-data-platform",
                    "doc": "https://wiki.company.com/schemas/order",
                },
            }
        },
    )

    subject: SubjectName
    type: SchemaType = Field(
        validation_alias=AliasChoices("schema_type", "type"),
        serialization_alias="type",
    )
    compatibility: CompatibilityMode | None = None
    schema_text: SchemaDefinition | None = Field(
        default=None,
        description="스키마 정의 텍스트",
        validation_alias=AliasChoices("schema", "schema_text"),
        serialization_alias="schema",
    )
    source: SchemaSource | None = None
    schema_hash: SchemaHash | None = Field(
        default=None,
        description="스키마 내용의 사전 계산된 해시",
    )
    references: list[SchemaReference] = Field(default_factory=list, max_length=16)
    metadata: SchemaMetadata | None = None
    reason: ReasonText | None = None
    dry_run_only: StrictBool = Field(
        default=False, description="true이면 dry-run에서만 검증하고 apply 시 제외"
    )

    @model_validator(mode="after")
    def validate_payload(self) -> SchemaBatchItem:
        """스키마 내용/소스 검증"""
        if not self.schema_text and not self.source:
            raise ValueError("schema or source must be provided")
        if self.schema_text and self.source and self.source.type is not SchemaSourceType.INLINE:
            raise ValueError("schema literal is only allowed with inline source or without source")
        return self

    @field_validator("references")
    @classmethod
    def validate_unique_reference_names(
        cls, value: Iterable[SchemaReference]
    ) -> list[SchemaReference]:
        """참조 이름 중복 검증"""
        references = list(value)
        names = [ref.name for ref in references]
        duplicates = {name for name in names if names.count(name) > 1}
        if duplicates:
            raise ValueError(f"duplicate reference name(s): {sorted(duplicates)}")
        return references


class SchemaBatchRequest(BaseModel):
    """스키마 배치 요청"""

    model_config = ConfigDict(
        extra="forbid",
        str_min_length=1,
        str_strip_whitespace=True,
        json_schema_extra={
            "example": {
                "kind": "SchemaBatch",
                "env": "prod",
                "change_id": "2025-09-25_001",
                "subjectStrategy": "TopicNameStrategy",
                "items": [
                    {
                        "subject": "prod.orders.created-value",
                        "type": "AVRO",
                        "compatibility": "FULL",
                        "schema": "{...}",
                        "metadata": {
                            "owner": "team-data-platform",
                            "doc": "https://wiki.company.com/schemas/order",
                        },
                    }
                ],
            }
        },
    )

    kind: StrictStr = Field(default="SchemaBatch", description="요청 종류")
    env: Environment
    change_id: ChangeId
    subject_strategy: SubjectStrategy = Field(
        default=SubjectStrategy.TOPIC_NAME,
        validation_alias=AliasChoices("subjectStrategy", "subject_strategy"),
        serialization_alias="subjectStrategy",
    )
    items: Annotated[
        list[SchemaBatchItem],
        Field(
            min_length=1,
            max_length=200,
            description="스키마 배치 항목",
            validation_alias=AliasChoices("items", "specs"),
            serialization_alias="items",
        ),
    ]

    @field_validator("kind")
    @classmethod
    def validate_kind(cls, value: StrictStr) -> StrictStr:
        """kind 필드 검증"""
        if value != "SchemaBatch":
            raise ValueError("kind must be 'SchemaBatch'")
        return value

    @field_validator("items")
    @classmethod
    def validate_unique_subjects(cls, items: list[SchemaBatchItem]) -> list[SchemaBatchItem]:
        """subject 중복 검증"""
        subjects = [item.subject for item in items]
        duplicates = {subject for subject in subjects if subjects.count(subject) > 1}
        if duplicates:
            raise ValueError(f"duplicate subjects detected: {sorted(duplicates)}")
        return items

    @model_validator(mode="after")
    def validate_env_consistency(self) -> SchemaBatchRequest:
        """환경 접두사 및 호환성 기본값 적용"""
        prefix = self.env.value
        adjusted_items: list[SchemaBatchItem] = []

        for item in self.items:
            subject_env = item.subject.split(".")[0]
            if subject_env != prefix:
                raise ValueError(
                    f"subject '{item.subject}' environment ({subject_env}) "
                    f"does not match batch environment ({prefix})"
                )

            if item.compatibility is None:
                default_mode = (
                    CompatibilityMode.FULL
                    if self.env is Environment.PROD
                    else CompatibilityMode.BACKWARD
                )
                adjusted_items.append(item.model_copy(update={"compatibility": default_mode}))
            else:
                adjusted_items.append(item)

        return self.model_copy(update={"items": adjusted_items})


class PolicyViolation(BaseModel):
    """정책 위반 정보"""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        json_schema_extra={
            "example": {
                "subject": "prod.tmp.experiment-value",
                "rule": "forbid.prefix",
                "message": "'tmp' prefix is forbidden in prod",
                "severity": "error",
                "field": "subject",
            }
        },
    )

    subject: SubjectName
    rule: ErrorRule
    message: ErrorMessage
    severity: ErrorSeverity = "error"
    field: ErrorField | None = None


class SchemaCompatibilityIssue(BaseModel):
    """호환성 위반 상세"""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        json_schema_extra={
            "example": {
                "path": "$.fields[1]",
                "message": "missing default for new field email",
                "type": "AVRO_MISSING_DEFAULT",
            }
        },
    )

    path: StrictStr
    message: ErrorMessage
    type: StrictStr


class SchemaCompatibilityReport(BaseModel):
    """호환성 검증 결과"""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        json_schema_extra={
            "example": {
                "subject": "prod.orders.created-value",
                "mode": "FULL",
                "is_compatible": True,
                "issues": [],
            }
        },
    )

    subject: SubjectName
    mode: CompatibilityMode
    is_compatible: StrictBool
    issues: list[SchemaCompatibilityIssue] = Field(default_factory=list)


class SchemaImpactRecord(BaseModel):
    """스키마 영향도 정보"""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        json_schema_extra={
            "example": {
                "subject": "prod.orders.created-value",
                "topics": ["prod.orders.created"],
                "consumers": ["consumer-group-1"],
            }
        },
    )

    subject: SubjectName
    topics: list[StrictStr] = Field(default_factory=list, max_length=50)
    consumers: list[StrictStr] = Field(default_factory=list, max_length=50)


class SchemaPlanItem(BaseModel):
    """스키마 배치 계획 항목"""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        json_schema_extra={
            "example": {
                "subject": "prod.orders.created-value",
                "action": "UPDATE",
                "current_version": 6,
                "target_version": 7,
                "diff": {"fields": {"email": "added with default ''"}},
            }
        },
    )

    subject: SubjectName
    action: PlanAction
    current_version: SchemaVersion | None = None
    target_version: SchemaVersion | None = None
    diff: dict[str, Any] = Field(default_factory=dict)


class SchemaBatchDryRunResponse(BaseModel):
    """스키마 배치 Dry-Run 응답"""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        json_schema_extra={
            "example": {
                "env": "prod",
                "change_id": "2025-09-25_001",
                "plan": [
                    {
                        "subject": "prod.orders.created-value",
                        "action": "UPDATE",
                        "current_version": 6,
                        "target_version": 7,
                        "diff": {"fields": {"email": "added"}},
                    }
                ],
                "violations": [],
                "compatibility": [
                    {
                        "subject": "prod.orders.created-value",
                        "mode": "FULL",
                        "is_compatible": True,
                        "issues": [],
                    }
                ],
                "impacts": [
                    {
                        "subject": "prod.orders.created-value",
                        "topics": ["prod.orders.created"],
                        "consumers": ["consumer-group-1"],
                    }
                ],
                "summary": {
                    "total_items": 1,
                    "update_count": 1,
                    "violation_count": 0,
                    "incompatible_count": 0,
                },
            }
        },
    )

    env: Environment
    change_id: ChangeId
    plan: list[SchemaPlanItem] = Field(default_factory=list)
    violations: list[PolicyViolation] = Field(default_factory=list)
    compatibility: list[SchemaCompatibilityReport] = Field(default_factory=list)
    impacts: list[SchemaImpactRecord] = Field(default_factory=list)
    summary: dict[str, int] = Field(default_factory=dict)


class SchemaArtifact(BaseModel):
    """스키마 저장 아티팩트 정보"""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        json_schema_extra={
            "example": {
                "subject": "prod.orders.created-value",
                "version": 7,
                "storage_url": "https://minio.local/schemas/prod/orders/7/schema.avsc",
                "checksum": "5b2c3a9f",
            }
        },
    )

    subject: SubjectName
    version: SchemaVersion
    storage_url: StorageUrl
    checksum: SchemaHash | None = None


class SchemaDeleteImpactResponse(BaseModel):
    """스키마 삭제 영향도 분석 응답"""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "subject": "prod.orders.created-value",
                "current_version": 15,
                "total_versions": 15,
                "affected_topics": ["prod.orders.created"],
                "warnings": [
                    "다음 토픽이 이 스키마를 사용 중일 수 있습니다: prod.orders.created",
                    "이 스키마는 15개의 버전이 있습니다. 삭제 시 모든 버전이 제거됩니다.",
                    "프로덕션 환경의 스키마입니다. 삭제 전 반드시 영향도를 확인하세요.",
                ],
                "safe_to_delete": False,
            }
        },
    )

    subject: SubjectName
    current_version: int | None = Field(description="현재 버전 번호")
    total_versions: int = Field(description="총 버전 개수")
    affected_topics: list[str] = Field(default_factory=list, description="영향받는 토픽 목록")
    warnings: list[str] = Field(default_factory=list, description="경고 메시지 목록")
    safe_to_delete: bool = Field(description="안전 삭제 가능 여부")


class SchemaBatchApplyResponse(BaseModel):
    """스키마 배치 Apply 응답"""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        json_schema_extra={
            "example": {
                "env": "prod",
                "change_id": "2025-09-25_001",
                "registered": ["prod.orders.created-value"],
                "skipped": [],
                "failed": [],
                "audit_id": "audit_12345",
                "artifacts": [
                    {
                        "subject": "prod.orders.created-value",
                        "version": 7,
                        "storage_url": "https://minio/...",
                        "checksum": "5b2c3a9f",
                    }
                ],
                "summary": {
                    "total_items": 1,
                    "registered_count": 1,
                    "skipped_count": 0,
                    "failed_count": 0,
                },
            }
        },
    )

    env: Environment
    change_id: ChangeId
    registered: list[SubjectName] = Field(default_factory=list)
    skipped: list[SubjectName] = Field(default_factory=list)
    failed: list[dict[str, StrictStr]] = Field(default_factory=list)
    audit_id: AuditId
    artifacts: list[SchemaArtifact] = Field(default_factory=list)
    summary: dict[str, int] = Field(default_factory=dict)


class SchemaUploadResponse(BaseModel):
    """스키마 업로드 응답"""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        json_schema_extra={
            "example": {
                "upload_id": "upload_20250925_001",
                "objects": [
                    {
                        "subject": "prod.orders.created-value",
                        "version": 7,
                        "storage_url": "https://minio/...",
                        "checksum": "5b2c3a9f",
                    }
                ],
                "summary": {
                    "total_files": 3,
                    "avro_count": 2,
                    "proto_count": 1,
                },
            }
        },
    )

    upload_id: StrictStr
    artifacts: list[SchemaArtifact] = Field(
        default_factory=list,
        validation_alias=AliasChoices("artifacts", "objects"),
        serialization_alias="artifacts",
    )
    summary: dict[str, int] = Field(default_factory=dict)
