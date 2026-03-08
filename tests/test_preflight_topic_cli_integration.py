from __future__ import annotations

import json
from typing import cast

import pytest
from typer.testing import CliRunner

from app.preflight.application.transport import PreflightTransport
from app.preflight.interface import cli
from app.schema.interface.schemas.request import SchemaBatchRequest
from app.topic.domain.models import DomainTopicApplyResult, DomainTopicPlan, DomainTopicPlanItem
from app.topic.domain.models.types_enum import DomainEnvironment, DomainPlanAction


class _UnusedSchemaTransport:
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
        _ = actor
        _ = actor_context
        raise AssertionError("schema transport should not be called in topic tests")

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
        _ = actor
        _ = storage_id
        _ = actor_context
        raise AssertionError("schema transport should not be called in topic tests")


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
        self.calls: list[tuple[str, str, str]] = []

    async def dry_run(
        self,
        cluster_id: str,
        request: object,
        actor: str,
        *,
        actor_context: dict[str, str] | None = None,
    ) -> object:
        _ = request
        _ = actor_context
        self.calls.append(("dry_run", cluster_id, actor))
        return self._dry_run_result

    async def apply(
        self,
        cluster_id: str,
        request: object,
        actor: str,
        approval_override: object | None = None,
        *,
        actor_context: dict[str, str] | None = None,
    ) -> object:
        _ = request
        _ = approval_override
        _ = actor_context
        self.calls.append(("apply", cluster_id, actor))
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
        audit_id="audit-topic-001",
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


def test_topic_dry_run_and_apply_cli_flow_uses_transport_seam_and_emits_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = CliRunner()
    dry_run_change_id = "chg-topic-dry-run-001"
    apply_change_id = "chg-topic-apply-001"

    topic_stub = _TopicTransportStub(
        dry_run_result=_build_plan(dry_run_change_id),
        apply_result=_build_apply_result(apply_change_id),
    )
    _install_transport_stub(monkeypatch, topic_stub)

    dry_run_result = runner.invoke(
        cli.cli_app,
        ["topic", "dry-run", "--cluster-id", "cluster-a", "--json"],
        input=_build_topic_payload(dry_run_change_id),
    )
    assert dry_run_result.exit_code == 0
    dry_run_envelope = _parse_envelope(dry_run_result.stdout)
    assert dry_run_envelope["operation"] == {
        "command": "preflight topic dry-run",
        "mode": "dry-run",
        "request_id": dry_run_change_id,
        "identifiers": {
            "cluster_id": "cluster-a",
            "registry_id": None,
            "storage_id": None,
        },
    }
    assert dry_run_envelope["result"] == {
        "status": "success",
        "summary": "evaluated 1 topic changes",
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
        ["topic", "apply", "--cluster-id", "cluster-a", "--json"],
        input=_build_topic_payload(apply_change_id),
    )
    assert apply_result.exit_code == 0
    apply_envelope = _parse_envelope(apply_result.stdout)
    assert apply_envelope["operation"] == {
        "command": "preflight topic apply",
        "mode": "apply",
        "request_id": apply_change_id,
        "identifiers": {
            "cluster_id": "cluster-a",
            "registry_id": None,
            "storage_id": None,
        },
    }
    assert apply_envelope["result"] == {
        "status": "success",
        "summary": "applied 1 of 1 topic changes",
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

    assert topic_stub.calls == [
        ("dry_run", "cluster-a", "system"),
        ("apply", "cluster-a", "system"),
    ]


def test_topic_apply_cli_approval_required_path_returns_exit_20_with_classified_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = CliRunner()
    change_id = "chg-topic-approval-001"

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
    envelope = _parse_envelope(result.stdout)
    assert envelope["operation"] == {
        "command": "preflight topic apply",
        "mode": "apply",
        "request_id": change_id,
        "identifiers": {
            "cluster_id": "cluster-a",
            "registry_id": None,
            "storage_id": None,
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

    assert topic_stub.calls == [("apply", "cluster-a", "system")]
