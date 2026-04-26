"""Schema Registry connection entities."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class SchemaRegistry:
    """Schema Registry connection information."""

    registry_id: str
    name: str
    url: str
    description: str | None = None
    auth_username: str | None = None
    auth_password: str | None = None
    ssl_ca_location: str | None = None
    ssl_cert_location: str | None = None
    ssl_key_location: str | None = None
    timeout: int = 30
    is_active: bool = True
    created_at: datetime
    updated_at: datetime

    def to_client_config(self) -> dict[str, str | int]:
        config: dict[str, str | int] = {"url": self.url, "timeout": self.timeout}
        if self.auth_username and self.auth_password:
            config["basic.auth.user.info"] = f"{self.auth_username}:{self.auth_password}"
        if self.ssl_ca_location:
            config["ssl.ca.location"] = self.ssl_ca_location
        if self.ssl_cert_location:
            config["ssl.certificate.location"] = self.ssl_cert_location
        if self.ssl_key_location:
            config["ssl.key.location"] = self.ssl_key_location
        return config


@dataclass(frozen=True, slots=True, kw_only=True)
class ConnectionTestResult:
    """Connection test result."""

    success: bool
    message: str
    latency_ms: float | None = None
    metadata: dict[str, str | int | bool] | None = None
