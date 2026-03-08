from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest
from typer.testing import CliRunner

from app.preflight.application.transport import PreflightTransport
from app.preflight.interface import cli
from app.schema.domain.models import (
    DomainSchemaApplyResult,
    DomainSchemaDiff,
    DomainSchemaPlan,
    DomainSchemaPlanItem,
)
from app.schema.domain.models.types_enum import DomainEnvironment, DomainPlanAction
from app.topic.interface.schemas.request import TopicBatchRequest

SNAPSHOT_DIR = Path(__file__).parent / "snapshots" / "preflight"


class _UnusedTopicTransport:
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
        _ = actor
        _ = actor_context
        raise AssertionError("topic transport should not be called in schema snapshot tests")

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
        raise AssertionError("topic transport should not be called in schema snapshot tests")


class _SchemaTransportStub:
    def __init__(
        self,
        *,
        dry_run_result: DomainSchemaPlan,
        apply_result: DomainSchemaApplyResult | None = None,
        apply_error: Exception | None = None,
    ) -> None:
        self._dry_run_result = dry_run_result
        self._apply_result = apply_result
        self._apply_error = apply_error

    async def dry_run(
        self,
        registry_id: str,
        request: object,
        actor: str,
        *,
        actor_context: dict[str, str] | None = None,
    ) -> object:
        _ = registry_id
        _ = request
        _ = actor
        _ = actor_context
        return self._dry_run_result

    async def apply(
        self,
        registry_id: str,
        request: object,
        actor: str,
        storage_id: str | None,
        *,
        actor_context: dict[str, str] | None = None,
    ) -> object:
        _ = registry_id
        _ = request
        _ = actor
        _ = storage_id
        _ = actor_context
        if self._apply_error is not None:
            raise self._apply_error
        if self._apply_result is None:
            raise AssertionError("apply_result must be provided when apply_error is not set")
        return self._apply_result


def _build_schema_payload(change_id: str) -> str:
    return json.dumps(
        {
            "kind": "SchemaBatch",
            "env": "dev",
            "change_id": change_id,
            "items": [
                {
                    "subject": "dev.orders.created-value",
                    "type": "AVRO",
                    "schema": '{"type":"record","name":"OrderCreated","fields":[{"name":"id","type":"string"}]}',
                }
            ],
        }
    )


def _build_plan(change_id: str) -> DomainSchemaPlan:
    return DomainSchemaPlan(
        change_id=change_id,
        env=DomainEnvironment.DEV,
        items=(
            DomainSchemaPlanItem(
                subject="dev.orders.created-value",
                action=DomainPlanAction.REGISTER,
                current_version=None,
                target_version=1,
                diff=DomainSchemaDiff(
                    type="new_registration",
                    changes=("register subject",),
                    current_version=None,
                    target_compatibility="BACKWARD",
                    schema_type="AVRO",
                ),
            ),
        ),
    )


def _build_apply_result(change_id: str) -> DomainSchemaApplyResult:
    return DomainSchemaApplyResult(
        change_id=change_id,
        env=DomainEnvironment.DEV,
        registered=("dev.orders.created-value",),
        skipped=(),
        failed=(),
        audit_id="audit-schema-snapshot-001",
    )


def _install_transport_stub(
    monkeypatch: pytest.MonkeyPatch, schema_stub: _SchemaTransportStub
) -> None:
    monkeypatch.setattr(
        cli,
        "_build_transport",
        lambda: PreflightTransport(
            topic_transport=_UnusedTopicTransport(),
            schema_transport=schema_stub,
        ),
    )


def _parse_envelope(stdout: str) -> dict[str, object]:
    parsed = cast(object, json.loads(stdout.strip()))
    if not isinstance(parsed, dict):
        raise AssertionError("expected JSON envelope object")
    return cast(dict[str, object], parsed)


def _load_snapshot(name: str) -> dict[str, object]:
    snapshot_path = SNAPSHOT_DIR / name
    payload = cast(object, json.loads(snapshot_path.read_text(encoding="utf-8")))
    if not isinstance(payload, dict):
        raise AssertionError(f"snapshot must contain an object: {snapshot_path}")
    return cast(dict[str, object], payload)


def test_schema_dry_run_cli_matches_success_contract_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = CliRunner()
    change_id = "chg-schema-snapshot-success-001"

    schema_stub = _SchemaTransportStub(
        dry_run_result=_build_plan(change_id),
        apply_result=_build_apply_result(change_id),
    )
    _install_transport_stub(monkeypatch, schema_stub)

    result = runner.invoke(
        cli.cli_app,
        ["schema", "dry-run", "--registry-id", "registry-a", "--json"],
        input=_build_schema_payload(change_id),
    )

    assert result.exit_code == 0
    assert _parse_envelope(result.stdout) == _load_snapshot("schema_dry_run_success.json")


def test_schema_apply_cli_matches_approval_required_failure_contract_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = CliRunner()
    change_id = "chg-schema-snapshot-failure-001"

    schema_stub = _SchemaTransportStub(
        dry_run_result=_build_plan(change_id),
        apply_error=RuntimeError("approval_override is required for this operation"),
    )
    _install_transport_stub(monkeypatch, schema_stub)

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
        ],
        input=_build_schema_payload(change_id),
    )

    assert result.exit_code == 20
    assert _parse_envelope(result.stdout) == _load_snapshot(
        "schema_apply_approval_required_failure.json"
    )
