"""Domain Events - Bounded Context 간 통신"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TypeAlias

from ..roles import UserRole

# Type Aliases
EventId: TypeAlias = str
AggregateId: TypeAlias = str
Actor: TypeAlias = str


@dataclass(frozen=True, slots=True)
class DomainEvent:
    """도메인 이벤트 베이스"""

    event_id: EventId
    aggregate_id: AggregateId
    occurred_at: datetime
    event_type: str


@dataclass(frozen=True, slots=True)
class SchemaRegisteredEvent:
    """스키마 등록 이벤트 - Schema Context → shared consumers"""

    event_id: EventId
    aggregate_id: AggregateId  # change_id
    occurred_at: datetime

    # Schema 정보
    subject: str
    version: int
    schema_type: str  # "AVRO", "JSON", "PROTOBUF"
    schema_id: int
    compatibility_mode: str

    # Subject Strategy (legacy naming metadata)
    subject_strategy: str  # naming strategy metadata

    # 메타데이터
    environment: str  # "dev", "stg", "prod"
    actor: Actor

    # 기본값이 있는 필드는 마지막에
    event_type: str = "schema.registered"
    actor_role: str = UserRole.ADMIN.value
