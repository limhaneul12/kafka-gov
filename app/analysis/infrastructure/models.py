"""Analysis Infrastructure SQLAlchemy Models"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Float, String, func
from sqlalchemy.orm import Mapped, mapped_column

from ...shared.database import Base


class TopicSchemaCorrelationModel(Base):
    """토픽-스키마 상관관계 테이블"""

    __tablename__ = "topic_schema_correlations"

    # 기본 키
    correlation_id: Mapped[str] = mapped_column(String(50), primary_key=True, comment="상관관계 ID")

    # 연결 정보
    topic_name: Mapped[str] = mapped_column(String(255), index=True, comment="토픽 이름")
    key_schema_subject: Mapped[str | None] = mapped_column(
        String(255), index=True, comment="Key 스키마 Subject"
    )
    value_schema_subject: Mapped[str | None] = mapped_column(
        String(255), index=True, comment="Value 스키마 Subject"
    )

    # 메타데이터
    environment: Mapped[str] = mapped_column(String(20), comment="환경")
    link_source: Mapped[str] = mapped_column(String(20), comment="연결 소스 (auto/manual/inferred)")
    confidence_score: Mapped[float] = mapped_column(Float, default=1.0, comment="신뢰도 점수")

    # 감사 정보
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), comment="생성 시간"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="수정 시간"
    )

    def __repr__(self) -> str:
        return f"<TopicSchemaCorrelation(topic={self.topic_name}, key={self.key_schema_subject}, value={self.value_schema_subject})>"


class SchemaImpactAnalysisModel(Base):
    """스키마 영향도 분석 결과 테이블"""

    __tablename__ = "schema_impact_analyses"

    # 기본 키
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="분석 ID")

    # 분석 대상
    subject: Mapped[str] = mapped_column(String(255), index=True, comment="스키마 Subject")

    # 분석 결과
    affected_topics: Mapped[dict[str, Any]] = mapped_column(
        JSON, comment="영향받는 토픽 목록 (JSON)"
    )
    total_impact_count: Mapped[int] = mapped_column(default=0, comment="영향 토픽 개수")
    risk_level: Mapped[str] = mapped_column(String(20), comment="위험도 (low/medium/high)")
    warnings: Mapped[dict[str, Any]] = mapped_column(JSON, comment="경고 메시지 (JSON)")

    # 감사 정보
    analyzed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), comment="분석 시간"
    )

    def __repr__(self) -> str:
        return f"<SchemaImpactAnalysis(subject={self.subject}, impact_count={self.total_impact_count}, risk={self.risk_level})>"
