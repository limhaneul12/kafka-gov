"""Topic Interface 스키마 - Pydantic v2 기반 DTO 및 검증 로직"""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictStr,
    field_validator,
    model_validator,
)

from .types import (
    AuditId,
    ChangeId,
    CleanupPolicy,
    CompressionType,
    DocumentUrl,
    Environment,
    ErrorField,
    ErrorMessage,
    ErrorRule,
    ErrorSeverity,
    MaxMessageBytes,
    MinInsyncReplicas,
    PartitionCount,
    PlanAction,
    PlanStatus,
    ReasonText,
    ReplicationFactor,
    RetentionMs,
    SegmentMs,
    SlaRequirement,
    TagName,
    TeamName,
    TopicAction,
    TopicName,
)


class TopicMetadata(BaseModel):
    """토픽 메타데이터"""

    model_config = ConfigDict(
        extra="forbid",
        str_min_length=1,
        str_strip_whitespace=True,
        frozen=True,
        json_schema_extra={
            "example": {
                "owner": "team-commerce",
                "sla": "P99<200ms",
                "doc": "https://wiki.company.com/streams/orders",
                "tags": ["pii", "critical"],
            }
        },
    )

    owner: TeamName
    sla: SlaRequirement | None = None
    doc: DocumentUrl | None = None
    tags: list[TagName] = Field(default_factory=list, max_length=10)


class TopicConfig(BaseModel):
    """토픽 설정"""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        json_schema_extra={
            "example": {
                "partitions": 12,
                "replication_factor": 3,
                "cleanup_policy": "compact",
                "compression_type": "zstd",
                "retention_ms": 604800000,
                "min_insync_replicas": 2,
                "max_message_bytes": 1048576,
            }
        },
    )

    partitions: PartitionCount
    replication_factor: ReplicationFactor
    cleanup_policy: CleanupPolicy = CleanupPolicy.DELETE
    compression_type: CompressionType = CompressionType.ZSTD
    retention_ms: RetentionMs | None = None
    min_insync_replicas: MinInsyncReplicas | None = None
    max_message_bytes: MaxMessageBytes | None = None
    segment_ms: SegmentMs | None = None

    @model_validator(mode="after")
    def validate_config_consistency(self) -> TopicConfig:
        """설정 일관성 검증"""
        if self.min_insync_replicas and self.min_insync_replicas > self.replication_factor:
            raise ValueError(
                f"min_insync_replicas ({self.min_insync_replicas}) cannot be greater than "
                f"replication_factor ({self.replication_factor})"
            )
        return self


class TopicItem(BaseModel):
    """토픽 배치 아이템"""

    model_config = ConfigDict(
        extra="forbid",
        str_min_length=1,
        str_strip_whitespace=True,
        frozen=True,
        json_schema_extra={
            "example": {
                "name": "prod.orders.created",
                "action": "upsert",
                "config": {
                    "partitions": 12,
                    "replication_factor": 3,
                    "cleanup_policy": "compact",
                    "compression_type": "zstd",
                    "retention_ms": 604800000,
                },
                "metadata": {
                    "owner": "team-commerce",
                    "sla": "P99<200ms",
                    "doc": "https://wiki.company.com/streams/orders",
                },
                "reason": "Business requirement change",
            }
        },
    )

    name: TopicName
    action: TopicAction
    config: TopicConfig | None = None
    metadata: TopicMetadata | None = None
    reason: ReasonText | None = None

    @model_validator(mode="after")
    def validate_action_requirements(self) -> TopicItem:
        """액션별 필수 필드 검증"""
        if self.action == TopicAction.DELETE:
            if not self.reason:
                raise ValueError("reason is required for delete action")
            if self.config is not None:
                raise ValueError("config should not be provided for delete action")
        else:
            if not self.config:
                raise ValueError(f"config is required for {self.action} action")
            if not self.metadata:
                raise ValueError(f"metadata is required for {self.action} action")

        return self


class TopicBatchRequest(BaseModel):
    """토픽 배치 요청"""

    model_config = ConfigDict(
        extra="forbid",
        str_min_length=1,
        str_strip_whitespace=True,
        json_schema_extra={
            "example": {
                "kind": "TopicBatch",
                "env": "prod",
                "change_id": "2025-09-25_001",
                "items": [
                    {
                        "name": "prod.orders.created",
                        "action": "upsert",
                        "config": {
                            "partitions": 12,
                            "replication_factor": 3,
                            "cleanup_policy": "compact",
                            "compression_type": "zstd",
                            "retention_ms": 604800000,
                        },
                        "metadata": {
                            "owner": "team-commerce",
                            "sla": "P99<200ms",
                            "doc": "https://wiki.company.com/streams/orders",
                        },
                    }
                ],
            }
        },
    )

    kind: PlanAction = "TopicBatch"
    env: Environment
    change_id: ChangeId
    items: Annotated[
        list[TopicItem],
        Field(min_length=1, max_length=100, description="토픽 아이템 목록"),
    ]

    @field_validator("items")
    @classmethod
    def validate_unique_topic_names(cls, v: list[TopicItem]) -> list[TopicItem]:
        """토픽 이름 중복 검증"""
        names = [item.name for item in v]
        if len(names) != len(set(names)):
            duplicates = [name for name in names if names.count(name) > 1]
            raise ValueError(f"Duplicate topic names found: {duplicates}")
        return v

    @model_validator(mode="after")
    def validate_env_consistency(self) -> TopicBatchRequest:
        """환경 일관성 검증"""
        for item in self.items:
            topic_env = item.name.split(".")[0]
            if topic_env != self.env.value:
                raise ValueError(
                    f"Topic {item.name} environment ({topic_env}) "
                    f"does not match batch environment ({self.env.value})"
                )
        return self


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


class TopicDetailResponse(BaseModel):
    """토픽 상세 응답"""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        json_schema_extra={
            "example": {
                "name": "prod.orders.created",
                "config": {
                    "partitions": 12,
                    "replication_factor": 3,
                    "cleanup_policy": "compact",
                    "compression_type": "zstd",
                    "retention_ms": 604800000,
                },
                "metadata": {
                    "owner": "team-commerce",
                    "sla": "P99<200ms",
                    "doc": "https://wiki.company.com/streams/orders",
                },
                "kafka_metadata": {
                    "partition_count": 12,
                    "leader_replicas": [1, 2, 3],
                    "created_at": "2025-09-25T10:00:00Z",
                },
            }
        },
    )

    name: TopicName
    config: TopicConfig
    metadata: TopicMetadata | None = None
    kafka_metadata: dict[str, Any] = Field(default_factory=dict)


class TopicPlanResponse(BaseModel):
    """토픽 계획 조회 응답"""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        json_schema_extra={
            "example": {
                "change_id": "2025-09-25_001",
                "env": "prod",
                "status": "applied",
                "created_at": "2025-09-25T10:00:00Z",
                "applied_at": "2025-09-25T10:05:00Z",
                "plan": [
                    {
                        "name": "prod.orders.created",
                        "action": "ALTER",
                        "diff": {"partitions": "8→12"},
                    }
                ],
            }
        },
    )

    change_id: ChangeId
    env: Environment
    status: PlanStatus
    created_at: StrictStr
    applied_at: StrictStr | None = None
    plan: list[TopicPlanItem] = Field(default_factory=list)
