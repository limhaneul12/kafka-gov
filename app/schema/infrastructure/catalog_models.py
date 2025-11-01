"""Schema Governance Catalog Models - OSS Advisory Mode

스키마 카탈로그를 위한 관찰/분석 전용 모델
차단(Enforce) 없이 가시성/조언만 제공
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Float, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database import Base


class SchemaSubjectModel(Base):
    """스키마 Subject 카탈로그 - 관찰 메타데이터

    Schema Registry의 Subject별 최신 정보 + 우리의 관찰/분석 결과
    """

    __tablename__ = "schema_subjects"

    # 기본 키
    subject: Mapped[str] = mapped_column(String(512), primary_key=True, comment="Subject 이름")

    # SR 메타데이터 (수집)
    latest_version: Mapped[int | None] = mapped_column(Integer, comment="최신 버전 번호")
    compat_level: Mapped[str | None] = mapped_column(
        String(50), comment="호환성 레벨 (BACKWARD, FORWARD 등)"
    )
    mode_readonly: Mapped[bool] = mapped_column(
        Boolean, default=False, comment="READONLY 모드 여부"
    )

    # 거버넌스 메타데이터 (추론/계산)
    env: Mapped[str | None] = mapped_column(
        String(20), comment="환경 (dev/stg/prod) - subject명에서 추출"
    )
    owner_team: Mapped[str | None] = mapped_column(
        String(100), comment="소유 팀 - naming에서 추출 또는 수동 태깅"
    )

    # 관찰/분석 점수 (Advisory)
    pii_score: Mapped[float] = mapped_column(
        Float, default=0.0, comment="PII 가능성 점수 (0.0~1.0)"
    )
    risk_score: Mapped[float] = mapped_column(
        Float, default=0.0, comment="리스크 점수 (0.0~1.0) - lint+drift 가중"
    )

    # 타임스탬프
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        comment="최종 동기화 시간",
    )

    # 인덱스
    __table_args__ = (
        Index("idx_env_team", "env", "owner_team"),
        Index("idx_risk_score", "risk_score"),
    )

    def __repr__(self) -> str:
        return f"<SchemaSubject(subject={self.subject}, latest_v={self.latest_version}, risk={self.risk_score:.2f})>"


class SchemaVersionModel(Base):
    """스키마 Version 상세 - 버전별 스냅샷

    각 버전의 스키마 본문 + SR 메타(references, rule_set, metadata) + 우리의 린트/분석 결과
    """

    __tablename__ = "schema_versions"

    # 기본 키 (복합키)
    subject: Mapped[str] = mapped_column(String(512), primary_key=True, comment="Subject 이름")
    version: Mapped[int] = mapped_column(Integer, primary_key=True, comment="버전 번호")

    # SR 메타데이터 (있는 그대로 저장)
    schema_type: Mapped[str] = mapped_column(
        String(50), comment="스키마 타입 (AVRO, JSON, PROTOBUF)"
    )
    schema_id: Mapped[int | None] = mapped_column(Integer, comment="SR 스키마 ID")
    schema_str: Mapped[str] = mapped_column(Text, comment="스키마 본문 (원본)")

    # 정규화/해시 (중복·변형 감지)
    schema_canonical_hash: Mapped[str | None] = mapped_column(
        String(64), comment="정규화 후 SHA-256 해시"
    )

    # SR 고급 메타 (rule_set, metadata.properties)
    references: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, comment="스키마 참조 (Schema Registry references)"
    )
    rule_set: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, comment="SR Rule Set (migration, domain rules)"
    )
    sr_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, comment="SR Metadata properties (tags, sensitive 등)"
    )

    # 우리의 분석 결과
    fields_meta: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, comment="필드별 메타 (타입, PII 후보, 네이밍 등)"
    )
    lint_report: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, comment="Lint 리포트 (violations: [{code, severity, rule, hint}])"
    )

    # 타임스탬프
    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        comment="SR 등록 시간 (또는 첫 수집 시간)",
    )
    synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        comment="마지막 동기화 시간",
    )

    # 인덱스
    __table_args__ = (
        Index("idx_subject_version", "subject", "version"),
        Index("idx_canonical_hash", "schema_canonical_hash"),
        Index("idx_schema_type", "schema_type"),
    )

    def __repr__(self) -> str:
        return f"<SchemaVersion(subject={self.subject}, v={self.version}, type={self.schema_type})>"


class ObservedUsageModel(Base):
    """관측된 스키마 사용 패턴 (Optional)

    실제 Kafka topic/consumer에서 사용 중인 스키마 버전 추적
    드리프트 감지용
    """

    __tablename__ = "observed_usage"

    # 기본 키 (복합키)
    subject: Mapped[str] = mapped_column(String(512), primary_key=True, comment="Subject 이름")
    version: Mapped[int] = mapped_column(Integer, primary_key=True, comment="버전 번호")

    # 관측 정보
    topics: Mapped[list[str] | None] = mapped_column(JSON, comment="사용 중인 토픽 목록")
    consumers: Mapped[list[str] | None] = mapped_column(JSON, comment="사용 중인 컨슈머 그룹 목록")

    # 타임스탬프
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        comment="최근 관측 시간",
    )

    # 인덱스
    __table_args__ = (Index("idx_last_seen", "last_seen_at"),)

    def __repr__(self) -> str:
        return f"<ObservedUsage(subject={self.subject}, v={self.version}, last_seen={self.last_seen_at})>"
