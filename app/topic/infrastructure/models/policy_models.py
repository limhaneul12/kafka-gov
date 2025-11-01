"""정책 ORM 모델"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Enum, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database import Base


class PolicyModel(Base):
    """정책 테이블 - 버전 관리 지원"""

    __tablename__ = "policies"

    # 기본 키
    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="레코드 ID"
    )

    # 정책 식별 (같은 policy_id로 여러 버전 저장)
    policy_id: Mapped[str] = mapped_column(String(36), nullable=False, comment="정책 UUID")
    version: Mapped[int] = mapped_column(Integer, nullable=False, comment="버전 번호 (1, 2, 3...)")

    # 정책 정보
    policy_type: Mapped[str] = mapped_column(
        Enum("naming", "guardrail", name="policy_type_enum"), nullable=False, comment="정책 타입"
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, comment="정책 이름")
    description: Mapped[str] = mapped_column(Text, nullable=False, comment="정책 설명")
    status: Mapped[str] = mapped_column(
        Enum("draft", "active", "archived", name="policy_status_enum"),
        nullable=False,
        comment="정책 상태",
    )

    # 정책 내용 (JSON)
    # - naming: CustomNamingRules의 dict
    # - guardrail: CustomGuardrailPreset의 dict
    content: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, comment="정책 내용 (JSON)"
    )

    # 적용 환경 (dev, stg, prod, total)
    target_environment: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="total", comment="적용 환경"
    )

    # 메타데이터
    created_by: Mapped[str] = mapped_column(String(255), nullable=False, comment="생성자")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), comment="생성 시간"
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True, comment="수정 시간"
    )
    activated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="활성화 시간 (ACTIVE 상태가 된 시점)"
    )

    # 제약 조건
    __table_args__ = (
        UniqueConstraint("policy_id", "version", name="uq_policy_version"),
        {"comment": "정책 버전 관리 테이블"},
    )

    def __repr__(self) -> str:
        return f"<Policy(id={self.policy_id}, version={self.version}, status={self.status})>"
