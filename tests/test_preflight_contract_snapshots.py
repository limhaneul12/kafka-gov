from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest
from typer.testing import CliRunner

from app.preflight.application.transport import PreflightTransport
from app.preflight.interface import cli
from app.schema.interface.schemas.request import SchemaBatchRequest
from app.topic.domain.models import DomainTopicApplyResult, DomainTopicPlan, DomainTopicPlanItem
from app.topic.domain.models.types_enum import DomainEnvironment, DomainPlanAction


SNAPSHOT_DIR = Path(__file__).parent / "snapshots" / "preflight"


class _UnusedSchemaTransport:
    async def dry_run(self, registry_id: str, request: SchemaBatchRequest, actor: str) -> object:
        _ = registry_id
        _ = request
        _ = actor
        raise AssertionError("schema transport should not be called in topic snapshot tests")

    async def apply(
        self,
        registry_id: str,
        request: SchemaBatchRequest,
        actor: str,
        storage_id: str | None,
    ) -> object:
        _ = registry_id
        _ = request
        _ = actor
        _ = storage_id
        raise AssertionError("schema transport should not be called in topic snapshot tests")


class _TopicTransportStub:
    def __init__(
        self,
        *,
        dry_run_result: DomainTopicPlan,
        apply_result: DomainTopicApplyResult | None = None,
        apply_error: Exception | None = None,
    ) -> None:
        self._dry_run_result: DomainTopicPlan = dry_run_result
        self._apply_result: DomainTopicApplyResult | None = apply_result
        self._apply_error: Exception | None = apply_error

    async def dry_run(self, cluster_id: str, request: object, actor: str) -> object:
        _ = cluster_id
        _ = request
        _ = actor
        return self._dry_run_result

    async def apply(
        self,
        cluster_id: str,
        request: object,
        actor: str,
        approval_override: object | None = None,
    ) -> object:
        _ = cluster_id
        _ = request
        _ = actor
        _ = approval_override
        if self._apply_error is not None:
            raise self._apply_error
        if self._apply_result is None:
            raise AssertionError("apply_result must be provided when apply_error is not set")
        return self._apply_result


def _build_topic_payload(change_id: str) -> str:
    return json.dumps(
        {
            "kind": "TopicBatch",
            "env": "dev",
            "change_id": change_id,
            "items": [
                {
                    "name": "dev.orders.created",
                    "action": "create",
                    "config": {
                        "partitions": 3,
                        "replication_factor": 2,
                    },
                    "metadata": {
                        "owners": ["team-platform"],
                    },
                }
            ],
        }
    )


def _build_plan(change_id: str) -> DomainTopicPlan:
    return DomainTopicPlan(
        change_id=change_id,
        env=DomainEnvironment.DEV,
        items=(
            DomainTopicPlanItem(
                name="dev.orders.created",
                action=DomainPlanAction.CREATE,
                diff={"partitions": "+3"},
                current_config=None,
                target_config={
                    "partitions": "3",
                    "replication.factor": "2",
                },
            ),
        ),
        violations=(),
    )


def _build_apply_result(change_id: str) -> DomainTopicApplyResult:
    return DomainTopicApplyResult(
        change_id=change_id,
        env=DomainEnvironment.DEV,
        applied=("dev.orders.created",),
        skipped=(),
        failed=(),
        audit_id="audit-topic-snapshot-001",
    )


def _install_transport_stub(
    monkeypatch: pytest.MonkeyPatch, topic_stub: _TopicTransportStub
) -> None:
    monkeypatch.setattr(
        cli,
        "_build_transport",
        lambda: PreflightTransport(
            topic_transport=topic_stub,
            schema_transport=_UnusedSchemaTransport(),
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


def test_topic_dry_run_cli_matches_success_contract_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = CliRunner()
    change_id = "chg-topic-snapshot-success-001"

    topic_stub = _TopicTransportStub(
        dry_run_result=_build_plan(change_id),
        apply_result=_build_apply_result(change_id),
    )
    _install_transport_stub(monkeypatch, topic_stub)

    result = runner.invoke(
        cli.cli_app,
        ["topic", "dry-run", "--cluster-id", "cluster-a", "--json"],
        input=_build_topic_payload(change_id),
    )

    assert result.exit_code == 0
    assert _parse_envelope(result.stdout) == _load_snapshot("topic_dry_run_success.json")


def test_topic_apply_cli_matches_approval_required_failure_contract_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = CliRunner()
    change_id = "chg-topic-snapshot-failure-001"

    topic_stub = _TopicTransportStub(
        dry_run_result=_build_plan(change_id),
        apply_error=RuntimeError("approval_override is required for this operation"),
    )
    _install_transport_stub(monkeypatch, topic_stub)

    result = runner.invoke(
        cli.cli_app,
        ["topic", "apply", "--cluster-id", "cluster-a", "--json"],
        input=_build_topic_payload(change_id),
    )

    assert result.exit_code == 20
    assert _parse_envelope(result.stdout) == _load_snapshot(
        "topic_apply_approval_required_failure.json"
    )
