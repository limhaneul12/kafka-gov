from __future__ import annotations

import json
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


class _UnusedTopicTransport:
    async def dry_run(self, cluster_id: str, request: TopicBatchRequest, actor: str) -> object:
        _ = cluster_id
        _ = request
        _ = actor
        raise AssertionError("topic transport should not be called in schema tests")

    async def apply(
        self,
        cluster_id: str,
        request: TopicBatchRequest,
        actor: str,
        approval_override: object | None = None,
    ) -> object:
        _ = cluster_id
        _ = request
        _ = actor
        _ = approval_override
        raise AssertionError("topic transport should not be called in schema tests")


class _SchemaTransportStub:
    def __init__(
        self,
        *,
        dry_run_result: DomainSchemaPlan,
        apply_result: DomainSchemaApplyResult | None = None,
        apply_error: Exception | None = None,
    ) -> None:
        self._dry_run_result: DomainSchemaPlan = dry_run_result
        self._apply_result: DomainSchemaApplyResult | None = apply_result
        self._apply_error: Exception | None = apply_error
        self.calls: list[tuple[str, str, str, str | None]] = []

    async def dry_run(self, registry_id: str, request: object, actor: str) -> object:
        _ = request
        self.calls.append(("dry_run", registry_id, actor, None))
        return self._dry_run_result

    async def apply(
        self,
        registry_id: str,
        request: object,
        actor: str,
        storage_id: str | None,
    ) -> object:
        _ = request
        self.calls.append(("apply", registry_id, actor, storage_id))
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
        audit_id="audit-schema-001",
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


def test_schema_dry_run_and_apply_cli_flow_uses_transport_seam_and_emits_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = CliRunner()
    dry_run_change_id = "chg-schema-dry-run-001"
    apply_change_id = "chg-schema-apply-001"

    schema_stub = _SchemaTransportStub(
        dry_run_result=_build_plan(dry_run_change_id),
        apply_result=_build_apply_result(apply_change_id),
    )
    _install_transport_stub(monkeypatch, schema_stub)

    dry_run_result = runner.invoke(
        cli.cli_app,
        ["schema", "dry-run", "--registry-id", "registry-a", "--json"],
        input=_build_schema_payload(dry_run_change_id),
    )
    assert dry_run_result.exit_code == 0
    dry_run_envelope = _parse_envelope(dry_run_result.stdout)
    assert dry_run_envelope["operation"] == {
        "command": "preflight schema dry-run",
        "mode": "dry-run",
        "request_id": dry_run_change_id,
        "identifiers": {
            "cluster_id": None,
            "registry_id": "registry-a",
            "storage_id": None,
        },
    }
    assert dry_run_envelope["result"] == {
        "status": "success",
        "summary": "evaluated 1 schema changes",
        "counts": {
            "total": 1,
            "planned": 1,
            "applied": 0,
            "unchanged": 0,
            "failed": 0,
            "warnings": 0,
        },
    }
    assert dry_run_envelope["error"] is None

    apply_result = runner.invoke(
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
        input=_build_schema_payload(apply_change_id),
    )
    assert apply_result.exit_code == 0
    apply_envelope = _parse_envelope(apply_result.stdout)
    assert apply_envelope["operation"] == {
        "command": "preflight schema apply",
        "mode": "apply",
        "request_id": apply_change_id,
        "identifiers": {
            "cluster_id": None,
            "registry_id": "registry-a",
            "storage_id": "storage-a",
        },
    }
    assert apply_envelope["result"] == {
        "status": "success",
        "summary": "applied 1 of 1 schema changes",
        "counts": {
            "total": 1,
            "planned": 1,
            "applied": 1,
            "unchanged": 0,
            "failed": 0,
            "warnings": 0,
        },
    }
    assert apply_envelope["error"] is None

    assert schema_stub.calls == [
        ("dry_run", "registry-a", "system", None),
        ("apply", "registry-a", "system", "storage-a"),
    ]


def test_schema_apply_cli_approval_required_path_returns_exit_20_with_classified_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = CliRunner()
    change_id = "chg-schema-approval-001"

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
    envelope = _parse_envelope(result.stdout)
    assert envelope["operation"] == {
        "command": "preflight schema apply",
        "mode": "apply",
        "request_id": change_id,
        "identifiers": {
            "cluster_id": None,
            "registry_id": "registry-a",
            "storage_id": "storage-a",
        },
    }
    result_payload = cast(dict[str, object], envelope["result"])
    counts = cast(dict[str, object], result_payload["counts"])
    assert result_payload["status"] == "failed"
    assert counts["failed"] == 1
    assert envelope["error"] == {
        "code": "approval_required",
        "message": "approval_override is required for this operation",
        "target": "approvalOverride",
        "retryable": False,
        "details": {},
    }

    assert schema_stub.calls == [("apply", "registry-a", "system", "storage-a")]
