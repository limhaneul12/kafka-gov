"""감사 로그 ORM 모델"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database import Base


class AuditLogModel(Base):
    """감사 로그 테이블"""

    __tablename__ = "audit_logs"

    # 기본 키
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="로그 ID")

    # 감사 정보
    change_id: Mapped[str] = mapped_column(String(100), comment="변경 ID")
    action: Mapped[str] = mapped_column(String(50), comment="액션")
    target: Mapped[str] = mapped_column(String(255), comment="대상 (토픽명)")
    team: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="팀 (토픽 소유자)")
    actor: Mapped[str] = mapped_column(String(100), comment="수행자")
    status: Mapped[str] = mapped_column(String(20), comment="상태")
    message: Mapped[str | None] = mapped_column(Text, comment="메시지")

    # 스냅샷 (변경 전후 상태)
    snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSON, comment="스냅샷 (JSON)")

    # 타임스탬프
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), comment="로그 시간"
    )

    def __repr__(self) -> str:
        return f"<AuditLog(id={self.id}, action={self.action}, target={self.target}, actor={self.actor})>"
