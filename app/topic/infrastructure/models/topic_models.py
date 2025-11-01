"""Topic 관련 ORM 모델"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database import Base


class TopicMetadataModel(Base):
    """토픽 메타데이터 테이블"""

    __tablename__ = "topic_metadata"

    # 기본 키
    topic_name: Mapped[str] = mapped_column(String(255), primary_key=True, comment="토픽 이름")

    # 메타데이터 필드
    owners: Mapped[dict[str, Any] | None] = mapped_column(JSON, comment="소유자 목록 (JSON 배열)")
    doc: Mapped[str | None] = mapped_column(Text, comment="문서/설명")
    tags: Mapped[dict[str, Any] | None] = mapped_column(JSON, comment="태그 (JSON)")
    environment: Mapped[str | None] = mapped_column(String(20), comment="환경 (dev/stg/prod)")
    slo: Mapped[str | None] = mapped_column(Text, comment="SLO (Service Level Objective)")
    sla: Mapped[str | None] = mapped_column(Text, comment="SLA (Service Level Agreement)")

    # 설정 정보 (JSON으로 저장)
    config: Mapped[dict[str, Any] | None] = mapped_column(JSON, comment="토픽 설정")

    # 감사 정보
    created_by: Mapped[str] = mapped_column(String(100), comment="생성자")
    updated_by: Mapped[str] = mapped_column(String(100), comment="수정자")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), comment="생성 시간"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="수정 시간"
    )

    def __repr__(self) -> str:
        return f"<TopicMetadata(name={self.topic_name}, owners={self.owners})>"


class TopicPlanModel(Base):
    """토픽 계획 테이블"""

    __tablename__ = "topic_plans"

    # 기본 키
    change_id: Mapped[str] = mapped_column(
        String(100), primary_key=True, comment="변경 ID"
    )  # 36 → 100

    # 계획 정보
    env: Mapped[str] = mapped_column(String(50), comment="환경 (dev/staging/prod)")
    plan_data: Mapped[dict[str, Any]] = mapped_column(JSON, comment="계획 데이터 (JSON)")

    # 상태 정보
    status: Mapped[str] = mapped_column(String(20), default="pending", comment="상태")
    can_apply: Mapped[bool] = mapped_column(default=True, comment="적용 가능 여부")

    # 감사 정보
    created_by: Mapped[str] = mapped_column(String(100), comment="생성자")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), comment="생성 시간"
    )
    updated_by: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="수정자")
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True, comment="수정 시간"
    )

    def __repr__(self) -> str:
        return f"<TopicPlan(change_id={self.change_id}, env={self.env}, status={self.status})>"


class TopicApplyResultModel(Base):
    """토픽 적용 결과 테이블"""

    __tablename__ = "topic_apply_results"

    # 기본 키
    change_id: Mapped[str] = mapped_column(
        String(100), primary_key=True, comment="변경 ID"
    )  # 36 → 100

    # 결과 정보
    result_data: Mapped[dict[str, Any]] = mapped_column(JSON, comment="적용 결과 (JSON)")
    success_count: Mapped[int] = mapped_column(default=0, comment="성공 개수")
    failure_count: Mapped[int] = mapped_column(default=0, comment="실패 개수")

    # 감사 정보
    applied_by: Mapped[str] = mapped_column(String(100), comment="적용자")
    applied_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), comment="적용 시간"
    )

    def __repr__(self) -> str:
        return f"<TopicApplyResult(change_id={self.change_id}, success={self.success_count}, failure={self.failure_count})>"
