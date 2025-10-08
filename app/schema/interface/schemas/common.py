"""Schema Interface - Common Schemas"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictStr, field_validator

from ..types.enums import CompatibilityMode, SchemaSourceType
from ..types.type_hints import (
    DocumentUrl,
    ErrorField,
    ErrorMessage,
    ErrorRule,
    ErrorSeverity,
    FileReference,
    PlanAction,
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

    @field_validator("type", mode="after")
    @classmethod
    def validate_payload(cls, value: SchemaSourceType, info) -> SchemaSourceType:
        """소스 타입에 따른 필수 필드 검증"""
        data = info.data
        inline = data.get("inline")
        file = data.get("file")
        yaml = data.get("yaml")

        if value is SchemaSourceType.INLINE:
            if not inline:
                raise ValueError("inline source requires 'inline' content")
            if file or yaml:
                raise ValueError("inline source cannot include file or yaml data")
        elif value is SchemaSourceType.FILE:
            if not file:
                raise ValueError("file source requires 'file' reference")
            if inline or yaml:
                raise ValueError("file source cannot include inline or yaml data")
        elif value is SchemaSourceType.YAML:
            if not yaml:
                raise ValueError("yaml source requires 'yaml' content")
            if inline or file:
                raise ValueError("yaml source cannot include inline or file data")
        return value


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
