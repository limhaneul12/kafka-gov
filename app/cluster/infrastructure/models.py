"""Cluster Infrastructure Models - SQLAlchemy 모델"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database import Base


class KafkaClusterModel(Base):
    """Kafka 클러스터 테이블"""

    __tablename__ = "kafka_clusters"

    # 기본 키
    cluster_id: Mapped[str] = mapped_column(String(100), primary_key=True, comment="클러스터 ID")

    # 기본 정보
    name: Mapped[str] = mapped_column(String(255), nullable=False, comment="클러스터 이름")
    bootstrap_servers: Mapped[str] = mapped_column(Text, nullable=False, comment="브로커 주소")
    description: Mapped[str | None] = mapped_column(Text, comment="설명")

    # 보안 설정
    security_protocol: Mapped[str] = mapped_column(
        String(50), default="PLAINTEXT", comment="보안 프로토콜"
    )
    sasl_mechanism: Mapped[str | None] = mapped_column(String(50), comment="SASL 메커니즘")
    sasl_username: Mapped[str | None] = mapped_column(String(255), comment="SASL 사용자명")
    sasl_password: Mapped[str | None] = mapped_column(String(255), comment="SASL 비밀번호 (암호화)")

    # SSL 설정
    ssl_ca_location: Mapped[str | None] = mapped_column(String(500), comment="SSL CA 인증서 경로")
    ssl_cert_location: Mapped[str | None] = mapped_column(String(500), comment="SSL 인증서 경로")
    ssl_key_location: Mapped[str | None] = mapped_column(String(500), comment="SSL 키 경로")

    # 타임아웃 설정
    request_timeout_ms: Mapped[int] = mapped_column(
        Integer, default=60000, comment="요청 타임아웃(ms)"
    )
    socket_timeout_ms: Mapped[int] = mapped_column(
        Integer, default=60000, comment="소켓 타임아웃(ms)"
    )

    # 상태
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, comment="활성화 여부")

    # 감사 정보
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), comment="생성 시간"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="수정 시간"
    )

    def __repr__(self) -> str:
        return f"<KafkaCluster(id={self.cluster_id}, name={self.name})>"


class SchemaRegistryModel(Base):
    """Schema Registry 테이블"""

    __tablename__ = "schema_registries"

    # 기본 키
    registry_id: Mapped[str] = mapped_column(String(100), primary_key=True, comment="레지스트리 ID")

    # 기본 정보
    name: Mapped[str] = mapped_column(String(255), nullable=False, comment="레지스트리 이름")
    url: Mapped[str] = mapped_column(Text, nullable=False, comment="레지스트리 URL")
    description: Mapped[str | None] = mapped_column(Text, comment="설명")

    # 인증 설정
    auth_username: Mapped[str | None] = mapped_column(String(255), comment="인증 사용자명")
    auth_password: Mapped[str | None] = mapped_column(String(255), comment="인증 비밀번호 (암호화)")

    # SSL 설정
    ssl_ca_location: Mapped[str | None] = mapped_column(String(500), comment="SSL CA 인증서 경로")
    ssl_cert_location: Mapped[str | None] = mapped_column(String(500), comment="SSL 인증서 경로")
    ssl_key_location: Mapped[str | None] = mapped_column(String(500), comment="SSL 키 경로")

    # 타임아웃 설정
    timeout: Mapped[int] = mapped_column(Integer, default=30, comment="요청 타임아웃(초)")

    # 상태
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, comment="활성화 여부")

    # 감사 정보
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), comment="생성 시간"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="수정 시간"
    )

    def __repr__(self) -> str:
        return f"<SchemaRegistry(id={self.registry_id}, name={self.name})>"


class ObjectStorageModel(Base):
    """Object Storage 테이블"""

    __tablename__ = "object_storages"

    # 기본 키
    storage_id: Mapped[str] = mapped_column(String(100), primary_key=True, comment="스토리지 ID")

    # 기본 정보
    name: Mapped[str] = mapped_column(String(255), nullable=False, comment="스토리지 이름")
    endpoint_url: Mapped[str] = mapped_column(Text, nullable=False, comment="엔드포인트 URL")
    description: Mapped[str | None] = mapped_column(Text, comment="설명")

    # 인증 설정
    access_key: Mapped[str] = mapped_column(String(255), nullable=False, comment="액세스 키")
    secret_key: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="시크릿 키 (암호화)"
    )

    # 버킷 설정
    bucket_name: Mapped[str] = mapped_column(String(255), nullable=False, comment="버킷명")
    region: Mapped[str] = mapped_column(String(100), default="us-east-1", comment="리전")

    # SSL 설정
    use_ssl: Mapped[bool] = mapped_column(Boolean, default=False, comment="SSL 사용 여부")

    # 상태
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, comment="활성화 여부")

    # 감사 정보
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), comment="생성 시간"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="수정 시간"
    )

    def __repr__(self) -> str:
        return f"<ObjectStorage(id={self.storage_id}, name={self.name})>"


class KafkaConnectModel(Base):
    """Kafka Connect 테이블"""

    __tablename__ = "kafka_connects"

    # 기본 키
    connect_id: Mapped[str] = mapped_column(String(100), primary_key=True, comment="Connect ID")

    # 연관 정보
    cluster_id: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="연관된 Kafka Cluster ID"
    )

    # 기본 정보
    name: Mapped[str] = mapped_column(String(255), nullable=False, comment="Connect 이름")
    url: Mapped[str] = mapped_column(Text, nullable=False, comment="Connect URL")
    description: Mapped[str | None] = mapped_column(Text, comment="설명")

    # 인증 설정
    auth_username: Mapped[str | None] = mapped_column(String(255), comment="인증 사용자명")
    auth_password: Mapped[str | None] = mapped_column(String(255), comment="인증 비밀번호 (암호화)")

    # 상태
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, comment="활성화 여부")

    # 감사 정보
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), comment="생성 시간"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="수정 시간"
    )

    def __repr__(self) -> str:
        return f"<KafkaConnect(id={self.connect_id}, name={self.name})>"
