from __future__ import annotations

import json

from typer.testing import CliRunner

from app.preflight.application.transport import PreflightTransport
from app.preflight.interface import cli
from app.schema.domain.models import DomainSchemaApplyResult
from app.schema.domain.models.types_enum import DomainEnvironment as SchemaEnvironment
from app.schema.interface.schemas.request import SchemaBatchRequest
from app.topic.domain.models import DomainTopicPlan
from app.topic.domain.models.types_enum import DomainEnvironment as TopicEnvironment
from app.topic.interface.schemas.request import TopicBatchRequest


class _TopicTransportRecorder:
    def __init__(self) -> None:
        self.actor: str | None = None
        self.actor_context: dict[str, str] | None = None

    async def dry_run(
        self,
        cluster_id: str,
        request: TopicBatchRequest,
        actor: str,
        *,
        actor_context: dict[str, str] | None = None,
    ) -> object:
        _ = cluster_id
        _ = request
        self.actor = actor
        self.actor_context = actor_context
        return DomainTopicPlan(
            change_id="chg-topic-actor-001",
            env=TopicEnvironment.DEV,
            items=(),
            violations=(),
            requested_total=1,
        )

    async def apply(
        self,
        cluster_id: str,
        request: TopicBatchRequest,
        actor: str,
        approval_override: object | None = None,
        *,
        actor_context: dict[str, str] | None = None,
    ) -> object:
        _ = cluster_id
        _ = request
        _ = actor
        _ = approval_override
        _ = actor_context
        raise AssertionError("topic apply should not be called")


class _SchemaTransportRecorder:
    def __init__(self) -> None:
        self.actor: str | None = None
        self.actor_context: dict[str, str] | None = None

    async def dry_run(
        self,
        registry_id: str,
        request: SchemaBatchRequest,
        actor: str,
        *,
        actor_context: dict[str, str] | None = None,
    ) -> object:
        _ = registry_id
        _ = request
        self.actor = actor
        self.actor_context = actor_context
        raise AssertionError("schema dry-run should not be called")

    async def apply(
        self,
        registry_id: str,
        request: SchemaBatchRequest,
        actor: str,
        storage_id: str | None,
        *,
        actor_context: dict[str, str] | None = None,
    ) -> object:
        _ = registry_id
        _ = request
        _ = storage_id
        self.actor = actor
        self.actor_context = actor_context
        return DomainSchemaApplyResult(
            change_id="chg-schema-actor-001",
            env=SchemaEnvironment.DEV,
            registered=(),
            skipped=("dev.orders.created-value",),
            failed=(),
            audit_id="audit-schema-actor-001",
            requested_total=1,
            planned_total=0,
        )


def _topic_payload(*, reason_key: str = "reason") -> str:
    return json.dumps(
        {
            "kind": "TopicBatch",
            "env": "dev",
            "change_id": "chg-topic-actor-001",
            "items": [
                {
                    "name": "dev.orders.created",
                    "action": "create",
                    "config": {"partitions": 1, "replication_factor": 1},
                    "metadata": {"owners": ["team-platform"]},
                    reason_key: "seasonal capacity increase",
                }
            ],
        }
    )


def _schema_payload(*, reason_key: str = "reason") -> str:
    return json.dumps(
        {
            "kind": "SchemaBatch",
            "env": "dev",
            "change_id": "chg-schema-actor-001",
            "items": [
                {
                    "subject": "dev.orders.created-value",
                    "type": "AVRO",
                    "schema": '{"type":"record","name":"OrderCreated","fields":[{"name":"id","type":"string"}]}',
                    reason_key: "documenting schema intent",
                }
            ],
        }
    )


def test_topic_cli_actor_flags_propagate_actor_context(monkeypatch) -> None:
    topic_transport = _TopicTransportRecorder()
    monkeypatch.setattr(
        cli,
        "_build_transport",
        lambda: PreflightTransport(
            topic_transport=topic_transport,
            schema_transport=_SchemaTransportRecorder(),
        ),
    )

    runner = CliRunner()
    result = runner.invoke(
        cli.cli_app,
        [
            "topic",
            "dry-run",
            "--cluster-id",
            "cluster-a",
            "--json",
            "--user-id",
            "u-123",
            "--username",
            "alice",
            "--source",
            "ci",
        ],
        input=_topic_payload(),
    )

    assert result.exit_code == 0
    assert topic_transport.actor == "alice"
    assert topic_transport.actor_context == {
        "user_id": "u-123",
        "username": "alice",
        "source": "ci",
    }


def test_topic_cli_actor_env_fallback_propagates_when_flags_absent(monkeypatch) -> None:
    topic_transport = _TopicTransportRecorder()
    monkeypatch.setenv("KAFKA_GOV_USER_ID", "u-456")
    monkeypatch.setenv("KAFKA_GOV_USERNAME", "platform-bot")
    monkeypatch.setenv("KAFKA_GOV_ACTOR_SOURCE", "automation")
    monkeypatch.setattr(
        cli,
        "_build_transport",
        lambda: PreflightTransport(
            topic_transport=topic_transport,
            schema_transport=_SchemaTransportRecorder(),
        ),
    )

    runner = CliRunner()
    result = runner.invoke(
        cli.cli_app,
        ["topic", "dry-run", "--cluster-id", "cluster-a", "--json"],
        input=_topic_payload(),
    )

    assert result.exit_code == 0
    assert topic_transport.actor == "platform-bot"
    assert topic_transport.actor_context == {
        "user_id": "u-456",
        "username": "platform-bot",
        "source": "automation",
    }


def test_topic_request_accepts_business_purpose_alias() -> None:
    request = TopicBatchRequest.model_validate(
        json.loads(_topic_payload(reason_key="business_purpose"))
    )

    assert request.items[0].reason == "seasonal capacity increase"


def test_schema_cli_actor_flags_propagate_actor_context(monkeypatch) -> None:
    schema_transport = _SchemaTransportRecorder()
    monkeypatch.setattr(
        cli,
        "_build_transport",
        lambda: PreflightTransport(
            topic_transport=_TopicTransportRecorder(),
            schema_transport=schema_transport,
        ),
    )

    runner = CliRunner()
    result = runner.invoke(
        cli.cli_app,
        [
            "schema",
            "apply",
            "--registry-id",
            "registry-a",
            "--storage-id",
            "storage-a",
            "--json",
            "--user-id",
            "u-789",
            "--username",
            "schema-bot",
            "--source",
            "api-gateway",
        ],
        input=_schema_payload(),
    )

    assert result.exit_code == 0
    assert schema_transport.actor == "schema-bot"
    assert schema_transport.actor_context == {
        "user_id": "u-789",
        "username": "schema-bot",
        "source": "api-gateway",
    }


def test_schema_request_accepts_business_purpose_camel_alias() -> None:
    request = SchemaBatchRequest.model_validate(
        json.loads(_schema_payload(reason_key="businessPurpose"))
    )

    assert request.items[0].reason == "documenting schema intent"
