"""Topic Request 스키마 - Pydantic v2 기반 요청 DTO"""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ..types import (
    ChangeId,
    CleanupPolicy,
    DocumentUrl,
    Environment,
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
                "doc": "https://wiki.company.com/streams/orders",
                "tags": ["pii", "critical"],
            }
        },
    )

    owner: TeamName
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
                "retention_ms": 604800000,
                "min_insync_replicas": 2,
                "max_message_bytes": 1048576,
            }
        },
    )

    partitions: int = Field(..., gt=0, description="파티션 수")
    replication_factor: int = Field(..., gt=0, description="복제 팩터")
    cleanup_policy: CleanupPolicy = CleanupPolicy.DELETE
    retention_ms: int | None = Field(default=None, description="보존 시간(밀리초)")
    min_insync_replicas: int | None = Field(default=None, description="최소 동기화 복제본 수")
    max_message_bytes: int | None = Field(default=None, description="최대 메시지 크기(바이트)")
    segment_ms: int | None = Field(default=None, description="세그먼트 롤링 시간(밀리초)")

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
                    "doc": "https://wiki.company.com/streams/orders",
                },
            }
        },
    )

    name: TopicName
    action: TopicAction
    config: TopicConfig | None = None
    metadata: TopicMetadata | None = None

    @model_validator(mode="after")
    def validate_action_requirements(self) -> TopicItem:
        """액션별 필수 필드 검증"""
        if self.action == TopicAction.DELETE:
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
                            "doc": "https://wiki.company.com/streams/orders",
                        },
                    }
                ],
            }
        },
    )

    kind: str = "TopicBatch"
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
