from __future__ import annotations

from datetime import UTC, datetime

from app.registry_connections.domain.models.entities import SchemaRegistry


def _now() -> datetime:
    return datetime(2026, 1, 1, tzinfo=UTC)


def _fixture_secret(label: str) -> str:
    return f"fixture-{label}-value"


def test_schema_registry_client_config_without_auth() -> None:
    registry = SchemaRegistry(
        registry_id="r1",
        name="registry-1",
        url="http://localhost:8081",
        created_at=_now(),
        updated_at=_now(),
    )

    cfg = registry.to_client_config()

    assert cfg["url"] == "http://localhost:8081"
    assert cfg["timeout"] == 30
    assert "basic.auth.user.info" not in cfg


def test_schema_registry_client_config_with_auth_and_ssl() -> None:
    registry = SchemaRegistry(
        registry_id="r2",
        name="registry-2",
        url="https://registry.local",
        auth_username="alice",
        auth_password=_fixture_secret("schema-registry"),
        ssl_ca_location="/tmp/ca",
        ssl_cert_location="/tmp/cert",
        ssl_key_location="/tmp/key",
        created_at=_now(),
        updated_at=_now(),
    )

    cfg = registry.to_client_config()

    assert cfg["basic.auth.user.info"] == f"alice:{_fixture_secret('schema-registry')}"
    assert cfg["ssl.ca.location"] == "/tmp/ca"
    assert cfg["ssl.certificate.location"] == "/tmp/cert"
    assert cfg["ssl.key.location"] == "/tmp/key"
