"""Domain Events - Bounded Context 간 통신"""

from __future__ import annotations

from datetime import datetime
from typing import TypeAlias

import msgspec

from ..roles import UserRole

# Type Aliases
EventId: TypeAlias = str
AggregateId: TypeAlias = str
Actor: TypeAlias = str


class DomainEvent(msgspec.Struct, frozen=True):
    """도메인 이벤트 베이스"""

    event_id: EventId
    aggregate_id: AggregateId
    occurred_at: datetime
    event_type: str


class SchemaRegisteredEvent(msgspec.Struct, frozen=True):
    """스키마 등록 이벤트 - Schema Context → Topic/Analysis Context"""

    event_id: EventId
    aggregate_id: AggregateId  # change_id
    occurred_at: datetime

    # Schema 정보
    subject: str
    version: int
    schema_type: str  # "AVRO", "JSON", "PROTOBUF"
    schema_id: int
    compatibility_mode: str

    # Subject Strategy (토픽 추론용)
    subject_strategy: str  # "TopicNameStrategy", etc.

    # 메타데이터
    environment: str  # "dev", "stg", "prod"
    actor: Actor

    # 기본값이 있는 필드는 마지막에
    event_type: str = "schema.registered"
    actor_role: str = UserRole.ADMIN.value


class TopicCreatedEvent(msgspec.Struct, frozen=True):
    """토픽 생성 이벤트 - Topic Context → Analysis Context"""

    event_id: EventId
    aggregate_id: AggregateId  # change_id
    occurred_at: datetime

    # Topic 정보
    topic_name: str
    partitions: int
    replication_factor: int

    # 메타데이터
    environment: str
    actor: Actor

    # 기본값이 있는 필드는 마지막에
    event_type: str = "topic.created"
    actor_role: str = UserRole.ADMIN.value


class TopicSchemaLinkedEvent(msgspec.Struct, frozen=True):
    """토픽-스키마 연결 이벤트 - Analysis Context 발행"""

    event_id: EventId
    aggregate_id: AggregateId
    occurred_at: datetime

    # 연결 정보
    topic_name: str
    schema_subject: str
    schema_type: str  # "key" or "value"
    link_source: str  # "auto" or "manual"

    # 메타데이터
    environment: str

    # 기본값이 있는 필드는 마지막에
    event_type: str = "topic_schema.linked"
    confidence_score: float = 1.0  # 자동 연결 신뢰도
