"""Cluster Domain Entities"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .types_enum import SaslMechanism, SecurityProtocol


@dataclass(frozen=True, slots=True, kw_only=True)
class KafkaCluster:
    """Kafka 클러스터 연결 정보 - Entity

    Note:
        ConnectionManager가 이 정보를 사용하여 AdminClient를 동적 생성
    """

    cluster_id: str
    name: str
    bootstrap_servers: str  # "broker1:9092,broker2:9092"
    description: str | None = None

    # 보안 설정
    security_protocol: SecurityProtocol = SecurityProtocol.PLAINTEXT
    sasl_mechanism: SaslMechanism | None = None
    sasl_username: str | None = None
    sasl_password: str | None = None  # 암호화된 값

    # SSL 설정 (선택적)
    ssl_ca_location: str | None = None
    ssl_cert_location: str | None = None
    ssl_key_location: str | None = None

    # 타임아웃 설정
    request_timeout_ms: int = 60000
    socket_timeout_ms: int = 60000

    # 메타데이터
    is_active: bool = True
    created_at: datetime
    updated_at: datetime

    def to_admin_config(self) -> dict[str, str | int]:
        """AdminClient 설정 딕셔너리 생성

        Returns:
            confluent_kafka.admin.AdminClient에 전달할 설정
        """
        config: dict[str, str | int] = {
            "bootstrap.servers": self.bootstrap_servers,
            "security.protocol": self.security_protocol.value,
            "request.timeout.ms": self.request_timeout_ms,
            "socket.timeout.ms": self.socket_timeout_ms,
        }

        # SASL 설정
        if self.sasl_mechanism:
            config["sasl.mechanism"] = self.sasl_mechanism.value
        if self.sasl_username:
            config["sasl.username"] = self.sasl_username
        if self.sasl_password:
            config["sasl.password"] = self.sasl_password

        # SSL 설정
        if self.ssl_ca_location:
            config["ssl.ca.location"] = self.ssl_ca_location
        if self.ssl_cert_location:
            config["ssl.certificate.location"] = self.ssl_cert_location
        if self.ssl_key_location:
            config["ssl.key.location"] = self.ssl_key_location

        return config


@dataclass(frozen=True, slots=True, kw_only=True)
class SchemaRegistry:
    """Schema Registry 연결 정보 - Entity

    Note:
        ConnectionManager가 이 정보를 사용하여 AsyncSchemaRegistryClient를 동적 생성
    """

    registry_id: str
    name: str
    url: str  # "http://localhost:8081"
    description: str | None = None

    # 인증 설정 (선택적)
    auth_username: str | None = None
    auth_password: str | None = None  # 암호화된 값

    # SSL 설정 (선택적)
    ssl_ca_location: str | None = None
    ssl_cert_location: str | None = None
    ssl_key_location: str | None = None

    # 타임아웃 설정
    timeout: int = 30

    # 메타데이터
    is_active: bool = True
    created_at: datetime
    updated_at: datetime

    def to_client_config(self) -> dict[str, str | int]:
        """Schema Registry Client 설정 딕셔너리 생성

        Returns:
            AsyncSchemaRegistryClient에 전달할 설정
        """
        config: dict[str, str | int] = {
            "url": self.url,
            "timeout": self.timeout,
        }

        # Basic Auth 설정
        if self.auth_username and self.auth_password:
            config["basic.auth.user.info"] = f"{self.auth_username}:{self.auth_password}"

        # SSL 설정
        if self.ssl_ca_location:
            config["ssl.ca.location"] = self.ssl_ca_location
        if self.ssl_cert_location:
            config["ssl.certificate.location"] = self.ssl_cert_location
        if self.ssl_key_location:
            config["ssl.key.location"] = self.ssl_key_location

        return config


@dataclass(frozen=True, slots=True, kw_only=True)
class ConnectionTestResult:
    """연결 테스트 결과 - Value Object"""

    success: bool
    message: str
    latency_ms: float | None = None  # 연결 지연시간 (ms)
    metadata: dict[str, str | int | bool] | None = None  # 추가 정보 (브로커 수, 버전 등)
