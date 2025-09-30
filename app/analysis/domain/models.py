"""Analysis Domain Models - msgspec 기반"""

from __future__ import annotations

from typing import TypeAlias

import msgspec

# Type Aliases
TopicName: TypeAlias = str
SubjectName: TypeAlias = str
CorrelationId: TypeAlias = str


class TopicSchemaCorrelation(msgspec.Struct, frozen=True):
    """토픽-스키마 상관관계 (Aggregate Root)"""

    correlation_id: CorrelationId
    topic_name: TopicName
    key_schema_subject: SubjectName | None
    value_schema_subject: SubjectName | None

    # 메타데이터
    environment: str
    link_source: str  # "auto", "manual", "inferred"
    confidence_score: float  # 0.0 ~ 1.0 (추론 신뢰도)

    def has_schema(self) -> bool:
        """스키마가 연결되어 있는지"""
        return self.key_schema_subject is not None or self.value_schema_subject is not None


class SchemaImpactAnalysis(msgspec.Struct, frozen=True):
    """스키마 영향도 분석 결과"""

    subject: SubjectName
    affected_topics: tuple[TopicName, ...]
    total_impact_count: int
    risk_level: str  # "low", "medium", "high"
    warnings: tuple[str, ...]


class TopicSchemaUsage(msgspec.Struct, frozen=True):
    """토픽의 스키마 사용 현황"""

    topic_name: TopicName
    key_schema: SubjectName | None
    value_schema: SubjectName | None
    schema_versions: dict[str, int]  # {"key": 5, "value": 12}
    last_updated: str  # ISO datetime
