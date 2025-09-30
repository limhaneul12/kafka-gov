"""애플리케이션 설정 - Pydantic Settings 기반"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def model_config_module(env_prefix: str) -> SettingsConfigDict:
    return SettingsConfigDict(
        env_prefix=env_prefix,
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


class DatabaseSettings(BaseSettings):
    """데이터베이스 설정"""

    model_config = model_config_module("DB_")

    # MySQL 연결 설정
    host: str = Field(default="localhost", description="데이터베이스 호스트")
    port: int = Field(default=3306, ge=1, le=65535, description="데이터베이스 포트")
    username: str = Field(default="kafka_gov", description="데이터베이스 사용자명")
    password: str = Field(default="password", description="데이터베이스 비밀번호")
    database: str = Field(default="kafka_gov", description="데이터베이스명")

    # 연결 풀 설정
    pool_size: int = Field(default=10, ge=1, le=100, description="연결 풀 크기")
    max_overflow: int = Field(default=20, ge=0, le=100, description="최대 오버플로우")
    pool_recycle: int = Field(default=3600, ge=300, description="연결 재사용 시간(초)")

    # 기타 설정
    echo: bool = Field(default=False, description="SQL 쿼리 로깅")

    @property
    def url(self) -> str:
        """데이터베이스 연결 URL 생성"""
        return f"mysql+aiomysql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"


class KafkaSettings(BaseSettings):
    """Kafka 설정"""

    model_config = model_config_module("KAFKA_")

    # Kafka 브로커 설정
    bootstrap_servers: str = Field(default="localhost:9092", description="Kafka 브로커 주소")
    security_protocol: str = Field(default="PLAINTEXT", description="보안 프로토콜")

    # AdminClient 설정
    request_timeout_ms: int = Field(default=30000, ge=1000, description="요청 타임아웃(ms)")
    retries: int = Field(default=3, ge=0, description="재시도 횟수")

    @field_validator("security_protocol")
    @classmethod
    def validate_security_protocol(cls, v: str) -> str:
        allowed = {"PLAINTEXT", "SSL", "SASL_PLAINTEXT", "SASL_SSL"}
        if v not in allowed:
            raise ValueError(f"security_protocol must be one of {allowed}")
        return v

    @property
    def admin_config(self) -> dict[str, Any]:
        """AdminClient 설정 딕셔너리"""
        return {
            "bootstrap.servers": self.bootstrap_servers,
            "security.protocol": self.security_protocol,
            "request.timeout.ms": self.request_timeout_ms,
            "retries": self.retries,
        }


class SchemaRegistrySettings(BaseSettings):
    """Schema Registry 설정"""

    model_config = model_config_module("SCHEMA_REGISTRY_")

    # Schema Registry 연결 설정
    url: str = Field(default="http://localhost:8081", description="Schema Registry URL")

    # 인증 설정 (선택적)
    username: str | None = Field(default=None, description="Basic Auth 사용자명")
    password: str | None = Field(default=None, description="Basic Auth 비밀번호")

    # SSL 설정 (선택적)
    ssl_ca_location: str | None = Field(default=None, description="SSL CA 인증서 경로")
    ssl_cert_location: str | None = Field(default=None, description="SSL 클라이언트 인증서 경로")
    ssl_key_location: str | None = Field(default=None, description="SSL 클라이언트 키 경로")

    # 타임아웃 설정
    timeout: int = Field(default=30, ge=1, description="요청 타임아웃(초)")

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not v.startswith(("http://", "https://")):
            raise ValueError("url must start with http:// or https://")
        return v.rstrip("/")

    @property
    def client_config(self) -> dict[str, Any]:
        """Schema Registry 클라이언트 설정 딕셔너리"""
        config = {
            "url": self.url,
            "timeout": self.timeout,
        }

        # Basic Auth 설정
        if self.username and self.password:
            config.update(
                {
                    "basic.auth.user.info": f"{self.username}:{self.password}",
                }
            )

        # SSL 설정
        if self.ssl_ca_location:
            config["ssl.ca.location"] = self.ssl_ca_location
        if self.ssl_cert_location:
            config["ssl.certificate.location"] = self.ssl_cert_location
        if self.ssl_key_location:
            config["ssl.key.location"] = self.ssl_key_location

        return config


class ObjectStorageSettings(BaseSettings):
    """오브젝트 스토리지 설정 (MinIO/S3)"""

    model_config = model_config_module("STORAGE_")

    # 연결 설정
    endpoint_url: str = Field(default="http://localhost:9000", description="스토리지 엔드포인트")
    access_key: str = Field(default="minioadmin", description="액세스 키")
    secret_key: str = Field(default="minioadmin", description="시크릿 키")
    bucket_name: str = Field(default="kafka-gov-schemas", description="버킷명")

    # 기타 설정
    region: str = Field(default="us-east-1", description="리전")
    use_ssl: bool = Field(default=False, description="SSL 사용 여부")


class AppSettings(BaseSettings):
    """전체 애플리케이션 설정"""

    model_config = model_config_module("APP_")

    # 애플리케이션 기본 설정
    app_name: str = Field(default="Kafka Governance", description="애플리케이션 이름")
    app_version: str = Field(default="1.0.0", description="애플리케이션 버전")
    debug: bool = Field(default=False, description="디버그 모드")

    # 환경 설정
    environment: str = Field(default="development", description="실행 환경")

    # 하위 설정들
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    kafka: KafkaSettings = Field(default_factory=KafkaSettings)
    schema_registry: SchemaRegistrySettings = Field(default_factory=SchemaRegistrySettings)
    storage: ObjectStorageSettings = Field(default_factory=ObjectStorageSettings)

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        allowed = {"development", "staging", "production"}
        if v not in allowed:
            raise ValueError(f"environment must be one of {allowed}")
        return v


@lru_cache
def get_settings() -> AppSettings:
    """설정 인스턴스 반환 (캐시됨)"""
    return AppSettings()


# 전역 설정 인스턴스
settings = get_settings()
