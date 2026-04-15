from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database import Base


class ApprovalRequestModel(Base):
    __tablename__ = "approval_requests"
    __table_args__ = (
        UniqueConstraint("request_id", name="uq_approval_request_request_id"),
        {"comment": "승인 요청 상태 저장 테이블"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    request_id: Mapped[str] = mapped_column(String(36), nullable=False, comment="승인 요청 UUID")
    resource_type: Mapped[str] = mapped_column(String(32), nullable=False, comment="리소스 타입")
    resource_name: Mapped[str] = mapped_column(String(255), nullable=False, comment="리소스 이름")
    change_type: Mapped[str] = mapped_column(String(64), nullable=False, comment="변경 유형")
    change_ref: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="change_id 등 외부 참조"
    )
    summary: Mapped[str] = mapped_column(Text, nullable=False, comment="요청 요약")
    justification: Mapped[str] = mapped_column(Text, nullable=False, comment="요청 사유")
    requested_by: Mapped[str] = mapped_column(String(100), nullable=False, comment="요청자")
    status: Mapped[str] = mapped_column(String(20), nullable=False, comment="상태")
    approver: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="승인/반려자")
    decision_reason: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="승인/반려 사유"
    )
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JSON, nullable=True, comment="추가 메타데이터"
    )
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, comment="요청 시간"
    )
    decided_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="결정 시간"
    )
