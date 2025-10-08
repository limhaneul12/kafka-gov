"""Connect Infrastructure Models - SQLAlchemy"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database import Base


class ConnectorMetadataModel(Base):
    """커넥터 메타데이터 테이블 (거버넌스용)

    Kafka Connect REST API는 커넥터 설정만 관리하므로,
    팀/태그/설명 등의 메타데이터는 별도로 저장합니다.
    """

    __tablename__ = "connector_metadata"

    # 기본 키
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4()), comment="메타데이터 ID"
    )

    # 외래 키
    connect_id: Mapped[str] = mapped_column(
        String(100),
        ForeignKey("kafka_connects.connect_id", ondelete="CASCADE"),
        nullable=False,
        comment="Kafka Connect ID",
    )

    # 커넥터 식별
    connector_name: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True, comment="커넥터 이름"
    )

    # 거버넌스 메타데이터
    team: Mapped[str | None] = mapped_column(String(100), index=True, comment="소유 팀")
    tags: Mapped[dict | None] = mapped_column(JSON, comment="태그 목록 (JSON Array)")
    description: Mapped[str | None] = mapped_column(Text, comment="커넥터 설명")
    owner: Mapped[str | None] = mapped_column(String(255), comment="담당자")

    # 감사 정보
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), comment="생성 시간"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="수정 시간"
    )

    # 복합 유니크 제약: connect_id + connector_name
    __table_args__ = (
        UniqueConstraint("connect_id", "connector_name", name="uq_connect_connector"),
    )

    def __repr__(self) -> str:
        return (
            f"<ConnectorMetadata(id={self.id}, connector={self.connector_name}, team={self.team})>"
        )
