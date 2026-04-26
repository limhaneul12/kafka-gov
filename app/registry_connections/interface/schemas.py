"""Schema Registry connection interface schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class SchemaRegistryCreateRequest(BaseModel):
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
    registry_id: str
    name: str
    url: str
    description: str | None
    auth_username: str | None
    ssl_ca_location: str | None
    ssl_cert_location: str | None
    ssl_key_location: str | None
    timeout: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ConnectionTestResponse(BaseModel):
    success: bool = Field(..., description="연결 성공 여부")
    message: str = Field(..., description="결과 메시지")
    latency_ms: float | None = Field(None, description="연결 지연시간 (ms)")
    metadata: dict[str, str | int | bool] | None = Field(None, description="추가 정보")

    class Config:
        from_attributes = True
