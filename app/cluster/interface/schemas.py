"""Cluster Interface Schemas - Pydantic 모델 (I/O 경계)"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

# ============================================================================
# Kafka Cluster Schemas
# ============================================================================


class KafkaClusterCreateRequest(BaseModel):
    """Kafka 클러스터 생성 요청"""

    cluster_id: str = Field(..., description="클러스터 ID (고유)", min_length=1, max_length=100)
    name: str = Field(..., description="클러스터 이름", min_length=1, max_length=255)
    bootstrap_servers: str = Field(..., description="브로커 주소 (예: broker1:9092,broker2:9092)")
    description: str | None = Field(None, description="설명")
    security_protocol: str = Field(
        default="PLAINTEXT", description="보안 프로토콜 (PLAINTEXT/SSL/SASL_PLAINTEXT/SASL_SSL)"
    )
    sasl_mechanism: str | None = Field(None, description="SASL 메커니즘")
    sasl_username: str | None = Field(None, description="SASL 사용자명")
    sasl_password: str | None = Field(None, description="SASL 비밀번호")
    ssl_ca_location: str | None = Field(None, description="SSL CA 인증서 경로")
    ssl_cert_location: str | None = Field(None, description="SSL 인증서 경로")
    ssl_key_location: str | None = Field(None, description="SSL 키 경로")
    request_timeout_ms: int = Field(default=60000, description="요청 타임아웃(ms)", ge=1000)
    socket_timeout_ms: int = Field(default=60000, description="소켓 타임아웃(ms)", ge=1000)


class KafkaClusterUpdateRequest(BaseModel):
    """Kafka 클러스터 수정 요청"""

    name: str = Field(..., description="클러스터 이름", min_length=1, max_length=255)
    bootstrap_servers: str = Field(..., description="브로커 주소")
    description: str | None = Field(None, description="설명")
    security_protocol: str = Field(default="PLAINTEXT", description="보안 프로토콜")
    sasl_mechanism: str | None = Field(None, description="SASL 메커니즘")
    sasl_username: str | None = Field(None, description="SASL 사용자명")
    sasl_password: str | None = Field(None, description="SASL 비밀번호")
    ssl_ca_location: str | None = Field(None, description="SSL CA 인증서 경로")
    ssl_cert_location: str | None = Field(None, description="SSL 인증서 경로")
    ssl_key_location: str | None = Field(None, description="SSL 키 경로")
    request_timeout_ms: int = Field(default=60000, description="요청 타임아웃(ms)", ge=1000)
    socket_timeout_ms: int = Field(default=60000, description="소켓 타임아웃(ms)", ge=1000)
    is_active: bool = Field(default=True, description="활성화 여부")


class KafkaClusterResponse(BaseModel):
    """Kafka 클러스터 응답"""

    cluster_id: str
    name: str
    bootstrap_servers: str
    description: str | None
    security_protocol: str
    sasl_mechanism: str | None
    sasl_username: str | None
    # sasl_password: 보안상 응답에서 제외
    ssl_ca_location: str | None
    ssl_cert_location: str | None
    ssl_key_location: str | None
    request_timeout_ms: int
    socket_timeout_ms: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Schema Registry Schemas
# ============================================================================


class SchemaRegistryCreateRequest(BaseModel):
    """Schema Registry 생성 요청"""

    registry_id: str = Field(..., description="레지스트리 ID (고유)", min_length=1, max_length=100)
    name: str = Field(..., description="레지스트리 이름", min_length=1, max_length=255)
    url: str = Field(..., description="레지스트리 URL (예: http://localhost:8081)")
    description: str | None = Field(None, description="설명")
    auth_username: str | None = Field(None, description="인증 사용자명")
    auth_password: str | None = Field(None, description="인증 비밀번호")
    ssl_ca_location: str | None = Field(None, description="SSL CA 인증서 경로")
    ssl_cert_location: str | None = Field(None, description="SSL 인증서 경로")
    ssl_key_location: str | None = Field(None, description="SSL 키 경로")
    timeout: int = Field(default=30, description="요청 타임아웃(초)", ge=1)


class SchemaRegistryUpdateRequest(BaseModel):
    """Schema Registry 수정 요청"""

    name: str = Field(..., description="레지스트리 이름", min_length=1, max_length=255)
    url: str = Field(..., description="레지스트리 URL")
    description: str | None = Field(None, description="설명")
    auth_username: str | None = Field(None, description="인증 사용자명")
    auth_password: str | None = Field(None, description="인증 비밀번호")
    ssl_ca_location: str | None = Field(None, description="SSL CA 인증서 경로")
    ssl_cert_location: str | None = Field(None, description="SSL 인증서 경로")
    ssl_key_location: str | None = Field(None, description="SSL 키 경로")
    timeout: int = Field(default=30, description="요청 타임아웃(초)", ge=1)
    is_active: bool = Field(default=True, description="활성화 여부")


class SchemaRegistryResponse(BaseModel):
    """Schema Registry 응답"""

    registry_id: str
    name: str
    url: str
    description: str | None
    auth_username: str | None
    # auth_password: 보안상 응답에서 제외
    ssl_ca_location: str | None
    ssl_cert_location: str | None
    ssl_key_location: str | None
    timeout: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Kafka Connect Schemas
# ============================================================================


class KafkaConnectCreateRequest(BaseModel):
    """Kafka Connect 생성 요청"""

    connect_id: str = Field(..., description="Connect ID (고유)", min_length=1, max_length=100)
    cluster_id: str = Field(
        ..., description="연관된 Kafka Cluster ID", min_length=1, max_length=100
    )
    name: str = Field(..., description="Connect 이름", min_length=1, max_length=255)
    url: str = Field(..., description="Connect URL (예: http://localhost:8083)")
    description: str | None = Field(None, description="설명")
    auth_username: str | None = Field(None, description="인증 사용자명")
    auth_password: str | None = Field(None, description="인증 비밀번호")


class KafkaConnectUpdateRequest(BaseModel):
    """Kafka Connect 수정 요청"""

    name: str = Field(..., description="Connect 이름", min_length=1, max_length=255)
    url: str = Field(..., description="Connect URL")
    description: str | None = Field(None, description="설명")
    auth_username: str | None = Field(None, description="인증 사용자명")
    auth_password: str | None = Field(None, description="인증 비밀번호")
    is_active: bool = Field(default=True, description="활성화 여부")


class KafkaConnectResponse(BaseModel):
    """Kafka Connect 응답"""

    connect_id: str
    cluster_id: str
    name: str
    url: str
    description: str | None
    auth_username: str | None
    # auth_password: 보안상 응답에서 제외
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Connection Test Schemas
# ============================================================================


class ConnectionTestResponse(BaseModel):
    """연결 테스트 응답"""

    success: bool = Field(..., description="연결 성공 여부")
    message: str = Field(..., description="결과 메시지")
    latency_ms: float | None = Field(None, description="연결 지연시간 (ms)")
    metadata: dict[str, str | int | bool] | None = Field(None, description="추가 정보")

    class Config:
        from_attributes = True
