from __future__ import annotations

import json
from typing import cast

import pytest
from typer.testing import CliRunner

from app.preflight.application.transport import PreflightTransport
from app.preflight.interface import cli
from app.schema.domain.models import DomainSchemaDiff, DomainSchemaPlan, DomainSchemaPlanItem
from app.schema.domain.models.types_enum import (
    DomainEnvironment as SchemaEnvironment,
    DomainPlanAction as SchemaPlanAction,
)
from app.shared.approval import ApprovalRequiredError, PolicyBlockedError
from app.shared.domain.policy_types import DomainResourceType
from app.shared.domain.preflight_policy import (
    DomainPolicyDecision,
    DomainPolicyPackEvaluation,
    DomainPolicyRuleResult,
    DomainRiskLevel,
)
from app.topic.domain.models import DomainTopicPlan, DomainTopicPlanItem
from app.topic.domain.models.types_enum import (
    DomainEnvironment as TopicEnvironment,
    DomainPlanAction as TopicPlanAction,
)


class _UnusedTopicTransport:
    async def dry_run(
        self,
        cluster_id: str,
        request: object,
        actor: str,
        *,
        actor_context: dict[str, str] | None = None,
    ) -> object:
        _ = cluster_id
        _ = request
        _ = actor
        _ = actor_context
        raise AssertionError("topic transport should not be called")

    async def apply(
        self,
        cluster_id: str,
        request: object,
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
        raise AssertionError("topic transport should not be called")


class _UnusedSchemaTransport:
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
        raise AssertionError("schema transport should not be called")

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
        raise AssertionError("schema transport should not be called")


class _TopicTransportStub:
    def __init__(
        self, *, dry_run_result: DomainTopicPlan | None = None, apply_error: Exception | None = None
    ) -> None:
        self._dry_run_result = dry_run_result
        self._apply_error = apply_error

    async def dry_run(
        self,
        cluster_id: str,
        request: object,
        actor: str,
        *,
        actor_context: dict[str, str] | None = None,
    ) -> object:
        _ = cluster_id
        _ = request
        _ = actor
        _ = actor_context
        if self._dry_run_result is None:
            raise AssertionError("dry_run_result must be set")
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
        _ = cluster_id
        _ = request
        _ = actor
        _ = approval_override
        _ = actor_context
        if self._apply_error is None:
            raise AssertionError("apply_error must be set")
        raise self._apply_error


class _SchemaTransportStub:
    def __init__(
        self,
        *,
        dry_run_result: DomainSchemaPlan | None = None,
        apply_error: Exception | None = None,
    ) -> None:
        self._dry_run_result = dry_run_result
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
        if self._dry_run_result is None:
            raise AssertionError("dry_run_result must be set")
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
        if self._apply_error is None:
            raise AssertionError("apply_error must be set")
        raise self._apply_error


def _topic_payload(change_id: str) -> str:
    return json.dumps(
        {
            "kind": "TopicBatch",
            "env": "dev",
            "change_id": change_id,
            "items": [
                {
                    "name": "dev.orders.created",
                    "action": "create",
                    "config": {"partitions": 3, "replication_factor": 2},
                    "metadata": {"owners": ["team-platform"]},
                }
            ],
        }
    )


def _schema_payload(change_id: str) -> str:
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


def _parse_envelope(stdout: str) -> dict[str, object]:
    parsed = cast(object, json.loads(stdout.strip()))
    if not isinstance(parsed, dict):
        raise AssertionError("expected JSON envelope object")
    return cast(dict[str, object], parsed)


def _approval_required_evaluation(resource_type: DomainResourceType) -> DomainPolicyPackEvaluation:
    resource_name = (
        "dev.orders.created"
        if resource_type is DomainResourceType.TOPIC
        else "dev.orders.created-value"
    )
    return DomainPolicyPackEvaluation(
        pack_name="policy-pack.v1",
        resource_type=resource_type,
        rules=(
            DomainPolicyRuleResult(
                code=f"{resource_type.value}.metadata.doc.missing",
                severity="warning",
                risk_level=DomainRiskLevel.HIGH,
                decision=DomainPolicyDecision.APPROVAL_REQUIRED,
                reason=f"{resource_type.value} metadata.doc is missing",
                resource_type=resource_type,
                resource_name=resource_name,
                field="metadata.doc",
            ),
        ),
    )


def _policy_blocked_evaluation() -> DomainPolicyPackEvaluation:
    return DomainPolicyPackEvaluation(
        pack_name="policy-pack.v1",
        resource_type=DomainResourceType.SCHEMA,
        rules=(
            DomainPolicyRuleResult(
                code="schema.compatibility.backward_incompatible",
                severity="error",
                risk_level=DomainRiskLevel.CRITICAL,
                decision=DomainPolicyDecision.REJECT,
                reason="schema is backward incompatible",
                resource_type=DomainResourceType.SCHEMA,
                resource_name="dev.orders.created-value",
                field="compatibility",
            ),
        ),
    )


def test_topic_dry_run_cli_emits_policy_metadata_from_domain_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    evaluation = _approval_required_evaluation(DomainResourceType.TOPIC)
    plan = DomainTopicPlan(
        change_id="chg-topic-policy-metadata-001",
        env=TopicEnvironment.DEV,
        items=(
            DomainTopicPlanItem(
                name="dev.orders.created",
                action=TopicPlanAction.CREATE,
                diff={"status": "new"},
                current_config=None,
                target_config={"partitions": "3", "replication.factor": "2"},
            ),
        ),
        violations=(),
        risk=evaluation.risk_metadata(),
        approval=evaluation.approval_metadata(mode="dry-run", approval_override_present=False),
        policy_evaluation=evaluation,
    )
    monkeypatch.setattr(
        cli,
        "_build_transport",
        lambda: PreflightTransport(
            topic_transport=_TopicTransportStub(dry_run_result=plan),
            schema_transport=_UnusedSchemaTransport(),
        ),
    )

    runner = CliRunner()
    result = runner.invoke(
        cli.cli_app,
        ["topic", "dry-run", "--cluster-id", "cluster-a", "--json"],
        input=_topic_payload("chg-topic-policy-metadata-001"),
    )

    assert result.exit_code == 0
    envelope = _parse_envelope(result.stdout)
    assert envelope["risk"] == {
        "level": "high",
        "blocking": False,
        "summary": "policy-pack.v1: 0 reject, 1 approval-required, 0 warn",
    }
    assert envelope["approval"] == {
        "required": True,
        "state": "pending",
        "summary": "approval required before apply for 1 rule(s)",
    }


def test_topic_apply_cli_approval_error_preserves_policy_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    evaluation = _approval_required_evaluation(DomainResourceType.TOPIC)
    monkeypatch.setattr(
        cli,
        "_build_transport",
        lambda: PreflightTransport(
            topic_transport=_TopicTransportStub(apply_error=ApprovalRequiredError(evaluation)),
            schema_transport=_UnusedSchemaTransport(),
        ),
    )

    runner = CliRunner()
    result = runner.invoke(
        cli.cli_app,
        ["topic", "apply", "--cluster-id", "cluster-a", "--json"],
        input=_topic_payload("chg-topic-policy-approval-001"),
    )

    assert result.exit_code == 20
    envelope = _parse_envelope(result.stdout)
    assert envelope["risk"] == {
        "level": "high",
        "blocking": False,
        "summary": "policy-pack.v1: 0 reject, 1 approval-required, 0 warn",
    }
    assert envelope["approval"] == {
        "required": True,
        "state": "pending",
        "summary": "approval required for 1 rule(s)",
    }


def test_schema_apply_cli_policy_block_error_preserves_policy_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    evaluation = _policy_blocked_evaluation()
    monkeypatch.setattr(
        cli,
        "_build_transport",
        lambda: PreflightTransport(
            topic_transport=_UnusedTopicTransport(),
            schema_transport=_SchemaTransportStub(apply_error=PolicyBlockedError(evaluation)),
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
        ],
        input=_schema_payload("chg-schema-policy-block-001"),
    )

    assert result.exit_code == 20
    envelope = _parse_envelope(result.stdout)
    assert envelope["risk"] == {
        "level": "critical",
        "blocking": True,
        "summary": "policy-pack.v1: 1 reject, 0 approval-required, 0 warn",
    }
    assert envelope["approval"] == {
        "required": False,
        "state": "rejected",
        "summary": "policy pack rejected the requested change",
    }
    assert cast(dict[str, object], envelope["error"])["code"] == "policy_blocked"


def test_schema_dry_run_cli_emits_policy_metadata_from_domain_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    evaluation = _approval_required_evaluation(DomainResourceType.SCHEMA)
    plan = DomainSchemaPlan(
        change_id="chg-schema-policy-metadata-001",
        env=SchemaEnvironment.DEV,
        items=(
            DomainSchemaPlanItem(
                subject="dev.orders.created-value",
                action=SchemaPlanAction.REGISTER,
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
        compatibility_reports=(),
        impacts=(),
        violations=(),
        risk=evaluation.risk_metadata(),
        approval=evaluation.approval_metadata(mode="dry-run", approval_override_present=False),
        policy_evaluation=evaluation,
    )
    monkeypatch.setattr(
        cli,
        "_build_transport",
        lambda: PreflightTransport(
            topic_transport=_UnusedTopicTransport(),
            schema_transport=_SchemaTransportStub(dry_run_result=plan),
        ),
    )

    runner = CliRunner()
    result = runner.invoke(
        cli.cli_app,
        ["schema", "dry-run", "--registry-id", "registry-a", "--json"],
        input=_schema_payload("chg-schema-policy-metadata-001"),
    )

    assert result.exit_code == 0
    envelope = _parse_envelope(result.stdout)
    assert envelope["approval"] == {
        "required": True,
        "state": "pending",
        "summary": "approval required before apply for 1 rule(s)",
    }
