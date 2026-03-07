from __future__ import annotations

from datetime import UTC, datetime

from app.cluster.domain.models.entities import KafkaCluster, SchemaRegistry
from app.cluster.domain.models.types_enum import SaslMechanism, SecurityProtocol


def _now() -> datetime:
    return datetime(2026, 1, 1, tzinfo=UTC)


def test_kafka_cluster_admin_config_plaintext() -> None:
    cluster = KafkaCluster(
        cluster_id="c1",
        name="cluster-1",
        bootstrap_servers="broker:9092",
        created_at=_now(),
        updated_at=_now(),
    )

    cfg = cluster.to_admin_config()

    assert cfg["bootstrap.servers"] == "broker:9092"
    assert cfg["security.protocol"] == "PLAINTEXT"
    assert "sasl.mechanism" not in cfg
    assert "ssl.ca.location" not in cfg


def test_kafka_cluster_admin_config_with_sasl_and_ssl() -> None:
    cluster = KafkaCluster(
        cluster_id="c2",
        name="cluster-2",
        bootstrap_servers="broker-a:9092,broker-b:9092",
        security_protocol=SecurityProtocol.SASL_SSL,
        sasl_mechanism=SaslMechanism.SCRAM_SHA_512,
        sasl_username="svc",
        sasl_password="secret",
        ssl_ca_location="/tmp/ca",
        ssl_cert_location="/tmp/cert",
        ssl_key_location="/tmp/key",
        created_at=_now(),
        updated_at=_now(),
    )

    cfg = cluster.to_admin_config()

    assert cfg["security.protocol"] == "SASL_SSL"
    assert cfg["sasl.mechanism"] == "SCRAM-SHA-512"
    assert cfg["sasl.username"] == "svc"
    assert cfg["sasl.password"] == "secret"
    assert cfg["ssl.ca.location"] == "/tmp/ca"
    assert cfg["ssl.certificate.location"] == "/tmp/cert"
    assert cfg["ssl.key.location"] == "/tmp/key"


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
        auth_password="pw",
        ssl_ca_location="/tmp/ca",
        ssl_cert_location="/tmp/cert",
        ssl_key_location="/tmp/key",
        created_at=_now(),
        updated_at=_now(),
    )

    cfg = registry.to_client_config()

    assert cfg["basic.auth.user.info"] == "alice:pw"
    assert cfg["ssl.ca.location"] == "/tmp/ca"
    assert cfg["ssl.certificate.location"] == "/tmp/cert"
    assert cfg["ssl.key.location"] == "/tmp/key"
