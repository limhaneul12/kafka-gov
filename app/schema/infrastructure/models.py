"""Schema 인프라스트럭처 SQLAlchemy 모델"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from ...shared.database import Base


class SchemaMetadataModel(Base):
    """스키마 메타데이터 테이블"""

    __tablename__ = "schema_metadata"

    # 기본 키
    subject: Mapped[str] = mapped_column(String(255), primary_key=True, comment="Subject 이름")

    # 메타데이터 필드
    owner: Mapped[str | None] = mapped_column(String(100), comment="소유자")
    doc: Mapped[str | None] = mapped_column(Text, comment="문서/설명")
    tags: Mapped[dict[str, Any] | None] = mapped_column(JSON, comment="태그 (JSON)")
    description: Mapped[str | None] = mapped_column(Text, comment="스키마 설명")

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
        return f"<SchemaMetadata(subject={self.subject}, owner={self.owner})>"


class SchemaPlanModel(Base):
    """스키마 계획 테이블"""

    __tablename__ = "schema_plans"

    # 기본 키
    change_id: Mapped[str] = mapped_column(
        String(100), primary_key=True, comment="변경 ID"
    )  # 36 → 100

    # 계획 정보
    env: Mapped[str] = mapped_column(String(50), comment="환경 (dev/stg/prod)")
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
        return f"<SchemaPlan(change_id={self.change_id}, env={self.env}, status={self.status})>"


class SchemaApplyResultModel(Base):
    """스키마 적용 결과 테이블"""

    __tablename__ = "schema_apply_results"

    # 기본 키
    change_id: Mapped[str] = mapped_column(
        String(100), primary_key=True, comment="변경 ID"
    )  # 36 → 100

    # 결과 정보
    result_data: Mapped[dict[str, Any]] = mapped_column(JSON, comment="적용 결과 (JSON)")
    registered_count: Mapped[int] = mapped_column(default=0, comment="등록 성공 개수")
    failed_count: Mapped[int] = mapped_column(default=0, comment="실패 개수")

    # 감사 정보
    applied_by: Mapped[str] = mapped_column(String(100), comment="적용자")
    applied_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), comment="적용 시간"
    )

    def __repr__(self) -> str:
        return f"<SchemaApplyResult(change_id={self.change_id}, registered={self.registered_count}, failed={self.failed_count})>"


class SchemaArtifactModel(Base):
    """스키마 아티팩트 테이블"""

    __tablename__ = "schema_artifacts"

    # 기본 키 (복합키)
    subject: Mapped[str] = mapped_column(String(255), primary_key=True, comment="Subject 이름")
    version: Mapped[int] = mapped_column(primary_key=True, comment="스키마 버전")

    # 아티팩트 정보
    storage_url: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="저장소 URL (optional)"
    )
    checksum: Mapped[str | None] = mapped_column(String(64), comment="체크섬")
    change_id: Mapped[str] = mapped_column(String(100), comment="변경 ID")  # 36 → 100

    # 메타데이터
    schema_type: Mapped[str] = mapped_column(String(20), comment="스키마 타입")
    file_size: Mapped[int | None] = mapped_column(comment="파일 크기 (bytes)")

    # 타임스탬프
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), comment="생성 시간"
    )

    def __repr__(self) -> str:
        return f"<SchemaArtifact(subject={self.subject}, version={self.version})>"


class SchemaUploadResultModel(Base):
    """스키마 업로드 결과 테이블"""

    __tablename__ = "schema_upload_results"

    # 기본 키
    upload_id: Mapped[str] = mapped_column(String(100), primary_key=True, comment="업로드 ID")

    # 업로드 정보
    change_id: Mapped[str] = mapped_column(String(100), comment="변경 ID")  # 36 → 100
    artifacts: Mapped[dict[str, Any]] = mapped_column(JSON, comment="업로드된 아티팩트 목록 (JSON)")
    artifact_count: Mapped[int] = mapped_column(default=0, comment="아티팩트 개수")

    # 감사 정보
    uploaded_by: Mapped[str] = mapped_column(String(100), comment="업로드한 사용자")
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), comment="업로드 시간"
    )

    def __repr__(self) -> str:
        return f"<SchemaUploadResult(upload_id={self.upload_id}, artifacts={self.artifact_count})>"


class SchemaAuditLogModel(Base):
    """스키마 감사 로그 테이블"""

    __tablename__ = "schema_audit_logs"

    # 기본 키
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="로그 ID")

    # 감사 정보
    change_id: Mapped[str] = mapped_column(
        String(100), comment="변경 ID"
    )  # 36 → 100 (긴 subject명 지원)
    action: Mapped[str] = mapped_column(String(50), comment="액션")
    target: Mapped[str] = mapped_column(String(255), comment="대상 (Subject명)")
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
        return f"<SchemaAuditLog(id={self.id}, action={self.action}, target={self.target}, actor={self.actor})>"
