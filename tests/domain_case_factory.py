from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any

from app.cluster.domain.models.entities import KafkaCluster, SchemaRegistry
from app.cluster.domain.models.types_enum import SaslMechanism, SecurityProtocol
from app.consumer.domain.models.group import ConsumerGroup, LagStats
from app.consumer.domain.types_enum import GroupState, PartitionAssignor
from app.schema.domain.models.plan_result import (
    DomainSchemaDiff,
    DomainSchemaPlan,
    DomainSchemaPlanItem,
)
from app.schema.domain.models.policy import DomainPolicyViolation as SchemaPolicyViolation
from app.schema.domain.models.policy import DomainSchemaCompatibilityReport
from app.schema.domain.models.spec_batch import DomainSchemaBatch, DomainSchemaSpec
from app.schema.domain.models.types_enum import (
    DomainCompatibilityMode,
    DomainEnvironment as SchemaEnvironment,
    DomainPlanAction as SchemaPlanAction,
    DomainSchemaSourceType,
    DomainSchemaType,
    DomainSubjectStrategy,
)
from app.schema.domain.models.value_objects import DomainSchemaSource
from app.shared.approval import (
    ApprovalOverride,
    assess_schema_batch_risk,
    assess_topic_batch_risk,
    ensure_approval,
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


def _fixture_secret(label: str) -> str:
    return f"fixture-{label}-value"


class DomainMockFactory:
    @staticmethod
    def kafka_cluster(*, with_sasl: bool = False, with_ssl: bool = False) -> KafkaCluster:
        return KafkaCluster(
            cluster_id="cluster-a",
            name="cluster-a",
            bootstrap_servers="broker-1:9092,broker-2:9092",
            security_protocol=SecurityProtocol.SASL_SSL
            if with_sasl
            else SecurityProtocol.PLAINTEXT,
            sasl_mechanism=SaslMechanism.SCRAM_SHA_256 if with_sasl else None,
            sasl_username="svc-user" if with_sasl else None,
            sasl_password=_fixture_secret("sasl") if with_sasl else None,
            ssl_ca_location="/tmp/ca.crt" if with_ssl else None,
            ssl_cert_location="/tmp/client.crt" if with_ssl else None,
            ssl_key_location="/tmp/client.key" if with_ssl else None,
            created_at=datetime(2026, 1, 1, tzinfo=UTC),
            updated_at=datetime(2026, 1, 1, tzinfo=UTC),
        )

    @staticmethod
    def schema_registry(*, with_auth: bool = False) -> SchemaRegistry:
        return SchemaRegistry(
            registry_id="registry-a",
            name="registry-a",
            url="http://localhost:8081",
            auth_username="sr-user" if with_auth else None,
            auth_password=_fixture_secret("schema-registry") if with_auth else None,
            created_at=datetime(2026, 1, 1, tzinfo=UTC),
            updated_at=datetime(2026, 1, 1, tzinfo=UTC),
        )

    @staticmethod
    def topic_spec(
        *,
        action: DomainTopicAction = DomainTopicAction.CREATE,
        name: str = "dev.orders.created",
        with_config: bool = True,
        with_metadata: bool = True,
    ) -> DomainTopicSpec:
        config = (
            DomainTopicConfig(
                partitions=3,
                replication_factor=2,
                cleanup_policy=DomainCleanupPolicy.DELETE,
                retention_ms=3600000,
                min_insync_replicas=1,
            )
            if with_config
            else None
        )
        metadata = (
            DomainTopicMetadata(
                owners=("team-platform",),
                doc="https://wiki.local/topic/orders",
                tags=("critical",),
            )
            if with_metadata
            else None
        )
        return DomainTopicSpec(name=name, action=action, config=config, metadata=metadata)

    @staticmethod
    def topic_batch(specs: tuple[DomainTopicSpec, ...]) -> DomainTopicBatch:
        return DomainTopicBatch(change_id="chg-topic-001", env=TopicEnvironment.DEV, specs=specs)

    @staticmethod
    def topic_plan(
        *, include_delete: bool = False, reduce_durability: bool = False
    ) -> DomainTopicPlan:
        create_item = DomainTopicPlanItem(
            name="dev.orders.created",
            action=TopicPlanAction.CREATE,
            diff={"partitions": "+2"},
            current_config={"replication.factor": "3", "min.insync.replicas": "2"},
            target_config={
                "replication.factor": "2" if reduce_durability else "3",
                "min.insync.replicas": "1" if reduce_durability else "2",
            },
        )
        items: tuple[DomainTopicPlanItem, ...] = (create_item,)
        if include_delete:
            items += (
                DomainTopicPlanItem(
                    name="dev.orders.to-delete",
                    action=TopicPlanAction.DELETE,
                    diff={"op": "delete"},
                ),
            )
        return DomainTopicPlan(
            change_id="plan-topic-001",
            env=TopicEnvironment.DEV,
            items=items,
            violations=(),
        )

    @staticmethod
    def schema_source_inline(
        schema_text: str = '{"type":"record","name":"Order","fields":[]}',
    ) -> DomainSchemaSource:
        return DomainSchemaSource(type=DomainSchemaSourceType.INLINE, inline=schema_text)

    @staticmethod
    def schema_spec(
        *,
        subject: str = "dev.orders-value",
        compatibility: DomainCompatibilityMode = DomainCompatibilityMode.BACKWARD,
        dry_run_only: bool = False,
    ) -> DomainSchemaSpec:
        return DomainSchemaSpec(
            subject=subject,
            schema_type=DomainSchemaType.AVRO,
            compatibility=compatibility,
            source=DomainMockFactory.schema_source_inline(),
            dry_run_only=dry_run_only,
        )

    @staticmethod
    def schema_batch(
        specs: tuple[DomainSchemaSpec, ...], env: SchemaEnvironment = SchemaEnvironment.DEV
    ) -> DomainSchemaBatch:
        return DomainSchemaBatch(
            change_id="chg-schema-001",
            env=env,
            subject_strategy=DomainSubjectStrategy.TOPIC_NAME,
            specs=specs,
        )

    @staticmethod
    def schema_plan(*, compatible: bool) -> DomainSchemaPlan:
        item = DomainSchemaPlanItem(
            subject="dev.orders-value",
            action=SchemaPlanAction.UPDATE,
            current_version=1,
            target_version=2,
            diff=DomainSchemaDiff(
                type="update",
                changes=("add field email",),
                current_version=1,
                target_compatibility="BACKWARD",
                schema_type="AVRO",
            ),
            schema='{"type":"record","name":"OrderV2","fields":[]}',
            current_schema='{"type":"record","name":"Order","fields":[]}',
        )
        report = DomainSchemaCompatibilityReport(
            subject="dev.orders-value",
            mode=DomainCompatibilityMode.BACKWARD,
            is_compatible=compatible,
            issues=(),
        )
        violations: tuple[SchemaPolicyViolation, ...] = ()
        return DomainSchemaPlan(
            change_id="plan-schema-001",
            env=SchemaEnvironment.DEV,
            items=(item,),
            compatibility_reports=(report,),
            violations=violations,
        )

    @staticmethod
    def consumer_group(
        *,
        state: GroupState = GroupState.STABLE,
        member_count: int = 3,
        total_lag: int = 120,
        p95_lag: int = 80,
    ) -> ConsumerGroup:
        return ConsumerGroup(
            cluster_id="cluster-a",
            group_id="group-orders",
            ts=datetime(2026, 1, 1, tzinfo=UTC),
            state=state,
            partition_assignor=PartitionAssignor.STICKY,
            member_count=member_count,
            topic_count=2,
            lag_stats=LagStats(
                total_lag=total_lag,
                mean_lag=float(total_lag) / 3,
                p50_lag=max(0, p95_lag // 2),
                p95_lag=p95_lag,
                max_lag=max(p95_lag, total_lag),
                partition_count=3,
            ),
        )

    @staticmethod
    def approval_override(hours: int = 1) -> ApprovalOverride:
        return ApprovalOverride(
            reason="Emergency production governance change",
            approver="oncall-platform",
            expires_at=datetime.now(UTC) + timedelta(hours=hours),
        )


@dataclass(slots=True)
class DomainCaseBuilder:
    domain: str
    name: str
    payload: dict[str, Any]

    def build(self) -> dict[str, Any]:
        return {
            "domain": self.domain,
            "name": self.name,
            **self.payload,
        }


def build_domain_case_matrix() -> dict[str, list[dict[str, Any]]]:
    factory = DomainMockFactory()

    cluster_cases = [
        DomainCaseBuilder(
            domain="cluster",
            name="kafka_admin_config_plaintext",
            payload={
                "run": lambda: factory.kafka_cluster().to_admin_config(),
                "assert": lambda cfg: (
                    cfg["security.protocol"] == "PLAINTEXT"
                    and "sasl.mechanism" not in cfg
                    and cfg["bootstrap.servers"].startswith("broker-1")
                ),
            },
        ).build(),
        DomainCaseBuilder(
            domain="cluster",
            name="schema_registry_client_config_with_auth",
            payload={
                "run": lambda: factory.schema_registry(with_auth=True).to_client_config(),
                "assert": lambda cfg: cfg["basic.auth.user.info"]
                == f"sr-user:{_fixture_secret('schema-registry')}",
            },
        ).build(),
    ]

    topic_cases = [
        DomainCaseBuilder(
            domain="topic",
            name="topic_spec_fingerprint_and_env",
            payload={
                "run": lambda: factory.topic_spec().fingerprint(),
                "assert": lambda fp: isinstance(fp, str) and len(fp) == 16,
            },
        ).build(),
        DomainCaseBuilder(
            domain="topic",
            name="topic_batch_rejects_duplicate_names",
            payload={
                "expect_error": ValueError,
                "run": lambda: factory.topic_batch(
                    (
                        factory.topic_spec(name="dev.orders.created"),
                        factory.topic_spec(name="dev.orders.created"),
                    )
                ),
            },
        ).build(),
        DomainCaseBuilder(
            domain="topic",
            name="topic_delete_rejects_config",
            payload={
                "expect_error": ValueError,
                "run": lambda: factory.topic_spec(
                    action=DomainTopicAction.DELETE,
                    with_config=True,
                    with_metadata=False,
                ),
            },
        ).build(),
    ]

    schema_cases = [
        DomainCaseBuilder(
            domain="schema",
            name="schema_source_file_requires_file_reference",
            payload={
                "expect_error": ValueError,
                "run": lambda: DomainSchemaSource(type=DomainSchemaSourceType.FILE),
            },
        ).build(),
        DomainCaseBuilder(
            domain="schema",
            name="schema_batch_env_mismatch_rejected",
            payload={
                "expect_error": ValueError,
                "run": lambda: factory.schema_batch(
                    (factory.schema_spec(subject="prod.orders-value"),),
                    env=SchemaEnvironment.DEV,
                ),
            },
        ).build(),
        DomainCaseBuilder(
            domain="schema",
            name="schema_plan_can_apply_reflects_compatibility",
            payload={
                "run": lambda: (
                    factory.schema_plan(compatible=True).can_apply,
                    factory.schema_plan(compatible=False).can_apply,
                ),
                "assert": lambda result: result == (True, False),
            },
        ).build(),
    ]

    consumer_cases = [
        DomainCaseBuilder(
            domain="consumer",
            name="consumer_group_attention_when_rebalancing",
            payload={
                "run": lambda: factory.consumer_group(
                    state=GroupState.REBALANCING
                ).needs_attention(),
                "assert": lambda needs_attention: needs_attention is True,
            },
        ).build(),
        DomainCaseBuilder(
            domain="consumer",
            name="consumer_group_attention_when_empty",
            payload={
                "run": lambda: factory.consumer_group(
                    state=GroupState.EMPTY, member_count=0
                ).needs_attention(),
                "assert": lambda needs_attention: needs_attention is True,
            },
        ).build(),
        DomainCaseBuilder(
            domain="consumer",
            name="consumer_group_healthy_stable_case",
            payload={
                "run": lambda: factory.consumer_group().needs_attention(),
                "assert": lambda needs_attention: needs_attention is False,
            },
        ).build(),
    ]

    shared_cases = [
        DomainCaseBuilder(
            domain="shared",
            name="ensure_approval_requires_override_for_high_risk",
            payload={
                "expect_error": ValueError,
                "run": lambda: ensure_approval(
                    assess_topic_batch_risk(
                        SimpleNamespace(env=SimpleNamespace(value="prod")),
                        factory.topic_plan(include_delete=True),
                    ),
                    approval_override=None,
                ),
            },
        ).build(),
        DomainCaseBuilder(
            domain="shared",
            name="ensure_approval_accepts_override_for_high_risk",
            payload={
                "run": lambda: ensure_approval(
                    assess_schema_batch_risk(
                        factory.schema_batch(
                            (
                                factory.schema_spec(
                                    subject="prod.orders-value",
                                    compatibility=DomainCompatibilityMode.NONE,
                                ),
                            ),
                            env=SchemaEnvironment.PROD,
                        ),
                        factory.schema_plan(compatible=True),
                    ),
                    approval_override=factory.approval_override(),
                ),
                "assert": lambda payload: payload["risk"]["requires_approval"] is True
                and payload["approval_override"]["approver"] == "oncall-platform",
            },
        ).build(),
    ]

    return {
        "cluster": cluster_cases,
        "topic": topic_cases,
        "schema": schema_cases,
        "consumer": consumer_cases,
        "shared": shared_cases,
    }
