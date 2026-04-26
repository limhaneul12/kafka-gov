"""Schema Registry connection SQLAlchemy models."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database import Base


class SchemaRegistryModel(Base):
    __tablename__ = "schema_registries"

    registry_id: Mapped[str] = mapped_column(
        String(100), primary_key=True, nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    auth_username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    auth_password: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ssl_ca_location: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ssl_cert_location: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ssl_key_location: Mapped[str | None] = mapped_column(String(500), nullable=True)
    timeout: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    def __repr__(self) -> str:
        return f"<SchemaRegistry(id={self.registry_id}, name={self.name})>"
