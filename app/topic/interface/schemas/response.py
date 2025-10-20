"""Topic Response 스키마 - Pydantic v2 기반 응답 DTO"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from ..types import (
    AuditId,
    ChangeId,
    Environment,
    TeamName,
    TopicName,
)
from .common import PolicyViolation, TopicPlanItem


class FailureDetail(BaseModel):
    """개별 실패 상세 정보"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    topic_name: str | None = None  # 토픽 이름 (YAML 파싱 실패 시 None)
    failure_type: str  # "yaml_parsing", "validation", "policy_violation", "kafka_error"
    error_message: str  # 주요 에러 메시지
    violations: list[PolicyViolation] = Field(default_factory=list)  # 정책 위반 목록
    suggestions: list[str] = Field(default_factory=list)  # 수정 제안
    raw_error: str | None = None  # 원본 에러 (디버깅용)


class TopicBatchDryRunResponse(BaseModel):
    """토픽 배치 Dry-Run 응답"""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        json_schema_extra={
            "example": {
                "env": "prod",
                "change_id": "2025-09-25_001",
                "plan": [
                    {
                        "name": "prod.orders.created",
                        "action": "ALTER",
                        "diff": {"partitions": "8→12"},
                    }
                ],
                "violations": [
                    {
                        "name": "prod.tmp.experiment",
                        "rule": "forbid.prefix",
                        "message": "'tmp' prefix is forbidden in prod environment",
                    }
                ],
                "summary": {
                    "total_items": 2,
                    "create_count": 0,
                    "alter_count": 1,
                    "delete_count": 1,
                    "violation_count": 1,
                },
            }
        },
    )

    env: Environment
    change_id: ChangeId
    plan: list[TopicPlanItem] = Field(default_factory=list)
    violations: list[PolicyViolation] = Field(default_factory=list)
    summary: dict[str, int] = Field(default_factory=dict)


class TopicBatchApplyResponse(BaseModel):
    """토픽 배치 Apply 응답"""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        json_schema_extra={
            "example": {
                "env": "prod",
                "change_id": "2025-09-25_001",
                "applied": ["prod.orders.created"],
                "skipped": [],
                "failed": [],
                "audit_id": "audit_12345",
                "summary": {
                    "total_items": 1,
                    "applied_count": 1,
                    "skipped_count": 0,
                    "failed_count": 0,
                },
            }
        },
    )

    env: Environment
    change_id: ChangeId
    applied: list[TopicName] = Field(default_factory=list)
    skipped: list[TopicName] = Field(default_factory=list)
    failed: list[FailureDetail] = Field(default_factory=list)  # 상세 에러 리포트
    audit_id: AuditId
    summary: dict[str, int] = Field(default_factory=dict)


class YAMLBatchResult(BaseModel):
    """YAML 파일별 처리 결과"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    file_index: int  # 파일 순번 (0부터 시작)
    success: bool
    env: str | None = None
    change_id: str | None = None
    applied_count: int = 0
    failure: FailureDetail | None = None  # 실패 시 상세 정보


class TopicListItem(BaseModel):
    """토픽 목록 아이템"""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        json_schema_extra={
            "example": {
                "name": "dev.orders.created",
                "owners": ["team-commerce", "team-platform"],
                "tags": ["pii", "critical"],
                "partition_count": 12,
                "replication_factor": 3,
                "retention_ms": 604800000,
                "environment": "dev",
                "slo": "99.9% availability",
                "sla": "99.5% uptime",
            }
        },
    )

    name: TopicName
    owners: list[TeamName] = Field(default_factory=list, description="소유 팀 목록")
    doc: str | None = None
    tags: list[str] = Field(default_factory=list)
    partition_count: int | None = None
    replication_factor: int | None = None
    retention_ms: int | None = Field(default=None, description="보존 시간(밀리초)")
    environment: str
    slo: str | None = Field(default=None, description="Service Level Objective")
    sla: str | None = Field(default=None, description="Service Level Agreement")


class TopicListResponse(BaseModel):
    """토픽 목록 응답"""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        json_schema_extra={
            "example": {
                "topics": [
                    {
                        "name": "dev.orders.created",
                        "owner": "team-commerce",
                        "tags": ["pii", "critical"],
                        "partition_count": 12,
                        "replication_factor": 3,
                        "environment": "dev",
                    },
                    {
                        "name": "prod.payments.completed",
                        "owner": "team-payments",
                        "tags": ["finance"],
                        "partition_count": 24,
                        "replication_factor": 3,
                        "environment": "prod",
                    },
                ]
            }
        },
    )

    topics: list[TopicListItem]


class TopicBulkDeleteResponse(BaseModel):
    """토픽 일괄 삭제 응답"""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        json_schema_extra={
            "example": {
                "succeeded": ["dev.orders.created", "prod.payments.completed"],
                "failed": ["dev.orders.created", "prod.payments.completed"],
                "message": "Deleted 2 topics, 2 failed",
            }
        },
    )

    succeeded: list[str]
    failed: list[str]
    message: str
