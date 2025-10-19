"""Topic Domain Type Aliases"""

from __future__ import annotations

from typing import TypeAlias

# 타입 별칭
TopicName: TypeAlias = str
ChangeId: TypeAlias = str
TeamName: TypeAlias = str
DocumentUrl: TypeAlias = str
KafkaMetadata: TypeAlias = dict[str, int | str | dict]  # Kafka 메타데이터 (유연한 구조)
DBMetadata: TypeAlias = dict[str, str | None]  # DB 메타데이터
