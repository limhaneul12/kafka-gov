"""Schema Interface - Response Schemas"""

from __future__ import annotations

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, StrictStr

from ..types.enums import Environment
from ..types.type_hints import AuditId, ChangeId, SubjectName
from .common import (
    PolicyViolation,
    SchemaArtifact,
    SchemaCompatibilityReport,
    SchemaImpactRecord,
    SchemaPlanItem,
)


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
