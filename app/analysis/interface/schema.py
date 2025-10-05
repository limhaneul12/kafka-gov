"""Analysis Interface DTOs - Pydantic V2 (빡빡한 검증)"""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StrictFloat, StrictStr, StringConstraints

# 빡빡한 타입 정의
TopicName = Annotated[
    StrictStr,
    StringConstraints(
        min_length=1,
        max_length=255,
        pattern=r"^[a-zA-Z0-9._-]+$",
        strip_whitespace=True,
    ),
    Field(description="토픽 이름"),
]

SubjectName = Annotated[
    StrictStr,
    StringConstraints(
        min_length=1,
        max_length=255,
        pattern=r"^[a-z0-9._-]+(-key|-value)?$",
        strip_whitespace=True,
    ),
    Field(description="스키마 Subject"),
]

Environment = Annotated[
    StrictStr,
    StringConstraints(pattern=r"^(dev|stg|prod)$"),
    Field(description="환경"),
]

RiskLevel = Annotated[
    StrictStr,
    StringConstraints(pattern=r"^(low|medium|high)$"),
    Field(description="위험도"),
]


class TopicSchemaCorrelationResponse(BaseModel):
    """토픽-스키마 상관관계 응답"""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        json_schema_extra={
            "example": {
                "correlation_id": "corr_abc123def456",
                "topic_name": "prod.orders.created",
                "key_schema_subject": "prod.orders.created-key",
                "value_schema_subject": "prod.orders.created-value",
                "environment": "prod",
                "link_source": "auto",
                "confidence_score": 0.95,
            }
        },
    )

    correlation_id: StrictStr
    topic_name: TopicName
    key_schema_subject: SubjectName | None = None
    value_schema_subject: SubjectName | None = None
    environment: Environment
    link_source: StrictStr = Field(pattern=r"^(auto|manual|inferred)$")
    confidence_score: StrictFloat = Field(ge=0.0, le=1.0)


class SchemaImpactAnalysisResponse(BaseModel):
    """스키마 영향도 분석 응답"""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        json_schema_extra={
            "example": {
                "subject": "prod.orders.created-value",
                "affected_topics": ["prod.orders.created", "prod.orders.archive"],
                "total_impact_count": 2,
                "risk_level": "high",
                "warnings": [
                    "영향받는 토픽: prod.orders.created, prod.orders.archive",
                    "⚠️ 높은 위험도: 프로덕션 환경 또는 다수의 토픽에 영향",
                    "🚨 프로덕션 스키마: 변경 전 반드시 검토 필요",
                ],
            }
        },
    )

    subject: SubjectName
    affected_topics: list[TopicName] = Field(default_factory=list)
    total_impact_count: int = Field(ge=0)
    risk_level: RiskLevel
    warnings: list[StrictStr] = Field(default_factory=list, max_length=20)


class StatisticsResponse(BaseModel):
    """통계 응답"""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        json_schema_extra={
            "example": {
                "topic_count": 25,
                "schema_count": 42,
                "correlation_count": 30,
            }
        },
    )

    topic_count: int = Field(ge=0, description="총 토픽 수")
    schema_count: int = Field(ge=0, description="총 스키마 수")
    correlation_count: int = Field(ge=0, description="총 상관관계 수")
