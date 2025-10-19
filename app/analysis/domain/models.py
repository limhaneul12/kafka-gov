"""Analysis Domain Models - dataclass 기반"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias

# Type Aliases
TopicName: TypeAlias = str
SubjectName: TypeAlias = str
CorrelationId: TypeAlias = str


@dataclass(frozen=True, slots=True)
class TopicSchemaCorrelation:
    """토픽-스키마 상관관계 (Aggregate Root) - Value Object"""

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


@dataclass(frozen=True, slots=True)
class SchemaImpactAnalysis:
    """스키마 영향도 분석 결과 - Value Object"""

    subject: SubjectName
    affected_topics: tuple[TopicName, ...]
    total_impact_count: int
    risk_level: str  # "low", "medium", "high"
    warnings: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class TopicSchemaUsage:
    """토픽의 스키마 사용 현황 - Value Object"""

    topic_name: TopicName
    key_schema: SubjectName | None
    value_schema: SubjectName | None
    schema_versions: dict[str, int]  # {"key": 5, "value": 12}
    last_updated: str  # ISO datetime
