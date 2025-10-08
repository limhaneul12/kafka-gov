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
    failed: list[dict[str, str]] = Field(default_factory=list)
    audit_id: AuditId
    summary: dict[str, int] = Field(default_factory=dict)


class TopicListItem(BaseModel):
    """토픽 목록 아이템"""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        json_schema_extra={
            "example": {
                "name": "dev.orders.created",
                "owner": "team-commerce",
                "tags": ["pii", "critical"],
                "partition_count": 12,
                "replication_factor": 3,
                "environment": "dev",
            }
        },
    )

    name: TopicName
    owner: TeamName | None = None
    doc: str | None = None
    tags: list[str] = Field(default_factory=list)
    partition_count: int | None = None
    replication_factor: int | None = None
    environment: str


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
