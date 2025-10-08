"""Topic 공통 스키마 - 요청/응답 공통으로 사용되는 DTO"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, StrictStr

from ..types import (
    ErrorField,
    ErrorMessage,
    ErrorRule,
    ErrorSeverity,
    PlanAction,
    TopicName,
)


class TopicPlanItem(BaseModel):
    """토픽 계획 아이템"""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        json_schema_extra={
            "example": {
                "name": "prod.orders.created",
                "action": "ALTER",
                "diff": {"partitions": "8→12", "retention_ms": "259200000→604800000"},
                "current_config": {"partitions": 8, "replication_factor": 3},
                "target_config": {"partitions": 12, "replication_factor": 3},
            }
        },
    )

    name: TopicName
    action: PlanAction
    diff: dict[str, str] = Field(default_factory=dict, description="변경 사항")
    current_config: dict[str, Any] | None = None
    target_config: dict[str, Any] | None = None


class PolicyViolation(BaseModel):
    """정책 위반"""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        json_schema_extra={
            "example": {
                "name": "prod.tmp.experiment",
                "rule": "forbid.prefix",
                "message": "'tmp' prefix is forbidden in prod environment",
                "severity": "error",
                "field": "name",
            }
        },
    )

    name: TopicName
    rule: ErrorRule
    message: ErrorMessage
    severity: ErrorSeverity = "error"
    field: ErrorField | None = None


class KafkaCoreMetadata(BaseModel):
    """Kafka 핵심 메타데이터 (검증용 Pydantic 모델)

    - partition_count: 파티션 개수
    - leader_replicas: 리더 복제본 브로커 ID 목록
    - created_at: 생성 시각(문자열)
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        json_schema_extra={
            "example": {
                "partition_count": 12,
                "leader_replicas": [1, 2, 3],
                "created_at": "2025-09-25T10:00:00Z",
            }
        },
    )

    partition_count: int = Field(ge=1, le=1000, description="파티션 수")
    leader_replicas: list[int] = Field(default_factory=list)
    created_at: StrictStr | None = None
