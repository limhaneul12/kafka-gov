from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.schema.domain.models.plan_result import (
    DomainSchemaDiff,
    DomainSchemaPlan,
    DomainSchemaPlanItem,
)
from app.schema.domain.models.policy import (
    DomainSchemaCompatibilityIssue,
    DomainSchemaCompatibilityReport,
)
from app.schema.domain.models.spec_batch import DomainSchemaBatch, DomainSchemaSpec
from app.schema.domain.models.types_enum import (
    DomainCompatibilityMode,
    DomainEnvironment as SchemaEnvironment,
    DomainPlanAction as SchemaPlanAction,
    DomainSchemaSourceType,
    DomainSchemaType,
    DomainSubjectStrategy,
)
from app.schema.domain.models.value_objects import DomainSchemaMetadata, DomainSchemaSource
from app.schema.domain.policies.policy_pack import DefaultSchemaPolicyPackV1
from app.shared.approval import (
    ApprovalOverride,
    ApprovalRequiredError,
    PolicyBlockedError,
    ensure_approval,
)
from app.shared.domain.policy_types import (
    DomainPolicySeverity,
    DomainPolicyViolation,
    DomainResourceType,
)
from app.topic.domain.models.config import DomainTopicConfig, DomainTopicMetadata
from app.topic.domain.models.plan import DomainTopicPlan, DomainTopicPlanItem
from app.topic.domain.models.spec_batch import DomainTopicBatch, DomainTopicSpec
from app.topic.domain.models.types_enum import (
    DomainCleanupPolicy,
    DomainEnvironment as TopicEnvironment,
    DomainPlanAction as TopicPlanAction,
    DomainTopicAction,
)
from app.topic.domain.policies.policy_pack import DefaultTopicPolicyPackV1


def _topic_metadata(
    *, doc: str | None = "https://wiki.example/streams/orders"
) -> DomainTopicMetadata:
    return DomainTopicMetadata(owners=("team-platform",), doc=doc, tags=("critical",))


def _topic_config(
    *,
    partitions: int = 6,
    replication_factor: int = 3,
    cleanup_policy: DomainCleanupPolicy = DomainCleanupPolicy.DELETE,
    retention_ms: int | None = 7200000,
    min_insync_replicas: int | None = 2,
) -> DomainTopicConfig:
    return DomainTopicConfig(
        partitions=partitions,
        replication_factor=replication_factor,
        cleanup_policy=cleanup_policy,
        retention_ms=retention_ms,
        min_insync_replicas=min_insync_replicas,
    )


def _topic_plan_item(
    *,
    name: str,
    action: TopicPlanAction,
    current_config: dict[str, str] | None,
    target_config: dict[str, str] | None,
) -> DomainTopicPlanItem:
    return DomainTopicPlanItem(
        name=name,
        action=action,
        diff={"status": "changed"},
        current_config=current_config,
        target_config=target_config,
    )


def _inline_source(schema_text: str) -> DomainSchemaSource:
    return DomainSchemaSource(type=DomainSchemaSourceType.INLINE, inline=schema_text)


def _schema_spec(
    *,
    subject: str,
    env: SchemaEnvironment,
    schema: str,
    metadata: DomainSchemaMetadata | None,
    compatibility: DomainCompatibilityMode = DomainCompatibilityMode.BACKWARD,
) -> DomainSchemaSpec:
    _ = env
    return DomainSchemaSpec(
        subject=subject,
        schema_type=DomainSchemaType.AVRO,
        compatibility=compatibility,
        schema=schema,
        source=_inline_source(schema),
        metadata=metadata,
    )


def test_topic_policy_pack_rejects_partition_decrease_and_replication_factor_change() -> None:
    spec = DomainTopicSpec(
        name="prod.orders.created",
        action=DomainTopicAction.UPDATE,
        config=_topic_config(partitions=3, replication_factor=2),
        metadata=_topic_metadata(),
    )
    batch = DomainTopicBatch(
        change_id="chg-topic-reject-001",
        env=TopicEnvironment.PROD,
        specs=(spec,),
    )
    plan = DomainTopicPlan(
        change_id=batch.change_id,
        env=batch.env,
        items=(
            _topic_plan_item(
                name=spec.name,
                action=TopicPlanAction.ALTER,
                current_config={
                    "partitions": "5",
                    "replication_factor": "3",
                    "cleanup.policy": "delete",
                    "retention.ms": "7200000",
                    "min.insync.replicas": "2",
                },
                target_config={
                    "partitions": "3",
                    "replication_factor": "2",
                    "cleanup.policy": "delete",
                    "retention.ms": "7200000",
                    "min.insync.replicas": "2",
                },
            ),
        ),
        violations=(
            DomainPolicyViolation(
                resource_type=DomainResourceType.TOPIC,
                resource_name=spec.name,
                rule_id="naming.invalid",
                message="topic name does not match active naming policy",
                severity=DomainPolicySeverity.ERROR,
                field="name",
            ),
        ),
    )

    result = DefaultTopicPolicyPackV1().evaluate(batch, plan)

    assert result.evaluation.blocking is True
    assert result.evaluation.decision.value == "reject"
    codes = {rule.code for rule in result.evaluation.rules}
    assert "topic.partition.decrease.forbidden" in codes
    assert "topic.replication_factor.minimum" in codes
    assert "topic.replication_factor.change.forbidden" in codes
    with pytest.raises(PolicyBlockedError):
        ensure_approval(result.evaluation, None)


def test_topic_policy_pack_requires_approval_for_delete_and_retention_decrease() -> None:
    update_spec = DomainTopicSpec(
        name="stg.orders.created",
        action=DomainTopicAction.UPDATE,
        config=_topic_config(retention_ms=3600000),
        metadata=_topic_metadata(),
    )
    delete_spec = DomainTopicSpec(name="stg.orders.legacy", action=DomainTopicAction.DELETE)
    batch = DomainTopicBatch(
        change_id="chg-topic-approval-001",
        env=TopicEnvironment.STG,
        specs=(update_spec, delete_spec),
    )
    plan = DomainTopicPlan(
        change_id=batch.change_id,
        env=batch.env,
        items=(
            _topic_plan_item(
                name=update_spec.name,
                action=TopicPlanAction.ALTER,
                current_config={
                    "partitions": "6",
                    "replication_factor": "3",
                    "cleanup.policy": "delete",
                    "retention.ms": "7200000",
                    "min.insync.replicas": "2",
                },
                target_config={
                    "partitions": "6",
                    "replication_factor": "3",
                    "cleanup.policy": "delete",
                    "retention.ms": "3600000",
                    "min.insync.replicas": "2",
                },
            ),
            _topic_plan_item(
                name=delete_spec.name,
                action=TopicPlanAction.DELETE,
                current_config={"partitions": "3", "replication_factor": "2"},
                target_config=None,
            ),
        ),
        violations=(),
    )

    result = DefaultTopicPolicyPackV1().evaluate(batch, plan)

    assert result.evaluation.blocking is False
    assert result.evaluation.approval_required is True
    codes = {rule.code for rule in result.evaluation.rules}
    assert "topic.delete.requires_approval" in codes
    assert "topic.retention.decrease.requires_approval" in codes
    with pytest.raises(ApprovalRequiredError):
        ensure_approval(result.evaluation, None)

    approved = ensure_approval(
        result.evaluation,
        ApprovalOverride(
            reason="Approved after reviewing data retention impact",
            approver="platform-oncall",
            expires_at=datetime.now(UTC) + timedelta(hours=2),
        ),
    )
    assert approved["approval"]["state"] == "approved"


def test_schema_policy_pack_rejects_incompatible_required_field_addition() -> None:
    old_schema = '{"type":"record","name":"OrderCreated","fields":[{"name":"id","type":"string"}]}'
    new_schema = '{"type":"record","name":"OrderCreated","fields":[{"name":"id","type":"string"},{"name":"customer_id","type":"string"}]}'
    spec = _schema_spec(
        subject="prod.orders.created-value",
        env=SchemaEnvironment.PROD,
        schema=new_schema,
        metadata=DomainSchemaMetadata(owner="team-data", doc="https://wiki.example/schemas/order"),
        compatibility=DomainCompatibilityMode.FULL,
    )
    batch = DomainSchemaBatch(
        change_id="chg-schema-reject-001",
        env=SchemaEnvironment.PROD,
        subject_strategy=DomainSubjectStrategy.TOPIC_NAME,
        specs=(spec,),
    )
    incompatible_report = DomainSchemaCompatibilityReport(
        subject=spec.subject,
        mode=DomainCompatibilityMode.FULL,
        is_compatible=False,
        issues=(
            DomainSchemaCompatibilityIssue(
                path="$.fields[1]",
                message="field customer_id has no default",
                issue_type="AVRO_MISSING_DEFAULT",
            ),
        ),
    )
    plan = DomainSchemaPlan(
        change_id=batch.change_id,
        env=batch.env,
        items=(
            DomainSchemaPlanItem(
                subject=spec.subject,
                action=SchemaPlanAction.UPDATE,
                current_version=1,
                target_version=2,
                diff=DomainSchemaDiff(
                    type="update",
                    changes=("add field",),
                    current_version=1,
                    target_compatibility="FULL",
                    schema_type="AVRO",
                ),
                schema=new_schema,
                current_schema=old_schema,
            ),
        ),
        compatibility_reports=(incompatible_report,),
        violations=(),
    )

    result = DefaultSchemaPolicyPackV1().evaluate(batch, plan)

    assert result.evaluation.blocking is True
    codes = {rule.code for rule in result.evaluation.rules}
    assert "schema.compatibility.backward_incompatible" in codes
    assert "schema.field.required_without_default.forbidden" in codes


def test_schema_policy_pack_requires_approval_for_missing_metadata_and_enum_narrowing() -> None:
    old_schema = '{"type":"record","name":"OrderCreated","fields":[{"name":"status","type":{"type":"enum","name":"Status","symbols":["OPEN","CLOSED"]}}]}'
    new_schema = '{"type":"record","name":"OrderCreated","fields":[{"name":"status","type":{"type":"enum","name":"Status","symbols":["OPEN"]}}]}'
    spec = _schema_spec(
        subject="stg.orders.created-value",
        env=SchemaEnvironment.STG,
        schema=new_schema,
        metadata=None,
    )
    batch = DomainSchemaBatch(
        change_id="chg-schema-approval-001",
        env=SchemaEnvironment.STG,
        subject_strategy=DomainSubjectStrategy.TOPIC_NAME,
        specs=(spec,),
    )
    compatible_report = DomainSchemaCompatibilityReport(
        subject=spec.subject,
        mode=DomainCompatibilityMode.BACKWARD,
        is_compatible=True,
        issues=(),
    )
    plan = DomainSchemaPlan(
        change_id=batch.change_id,
        env=batch.env,
        items=(
            DomainSchemaPlanItem(
                subject=spec.subject,
                action=SchemaPlanAction.UPDATE,
                current_version=1,
                target_version=2,
                diff=DomainSchemaDiff(
                    type="update",
                    changes=("narrow enum",),
                    current_version=1,
                    target_compatibility="BACKWARD",
                    schema_type="AVRO",
                ),
                schema=new_schema,
                current_schema=old_schema,
            ),
        ),
        compatibility_reports=(compatible_report,),
        violations=(),
    )

    result = DefaultSchemaPolicyPackV1().evaluate(batch, plan)

    assert result.evaluation.blocking is False
    assert result.evaluation.approval_required is True
    codes = {rule.code for rule in result.evaluation.rules}
    assert "schema.metadata.missing" in codes
    assert "schema.enum_narrowing.requires_approval" in codes
