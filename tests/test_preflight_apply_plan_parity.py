from __future__ import annotations

import json
from typing import cast

import pytest

from app.cluster.domain.services import IConnectionManager
from app.schema.application.use_cases.batch import apply as schema_apply_module
from app.schema.application.use_cases.batch.apply import SchemaBatchApplyUseCase
from app.schema.domain.models import (
    DomainCompatibilityMode,
    DomainEnvironment as SchemaEnvironment,
    DomainSchemaBatch,
    DomainSchemaCompatibilityReport,
    DomainSchemaMetadata,
    DomainSchemaPlan,
    DomainSchemaSpec,
    DomainSchemaType,
    DomainSubjectStrategy,
    SchemaVersionInfo,
)
from app.schema.domain.repositories.interfaces import (
    ISchemaAuditRepository,
    ISchemaMetadataRepository,
    ISchemaPolicyRepository,
)
from app.shared.constants import AuditStatus
from app.topic.application.batch_use_cases import batch_apply as topic_apply_module
from app.topic.application.batch_use_cases.batch_apply import TopicBatchApplyUseCase
from app.topic.domain.models import (
    DomainCleanupPolicy,
    DomainEnvironment as TopicEnvironment,
    DomainTopicAction,
    DomainTopicBatch,
    DomainTopicConfig,
    DomainTopicMetadata,
    DomainTopicSpec,
)
from app.topic.domain.policies.management import IPolicyRepository
from app.topic.domain.repositories.interfaces import IAuditRepository, ITopicMetadataRepository


class _TopicConnectionManager:
    kafka_cluster_repo = None
    schema_registry_repo = None

    async def get_kafka_admin_client(self, cluster_id: str) -> object:
        _ = cluster_id
        return object()


class _TopicMetadataRepository:
    def __init__(self) -> None:
        self.saved_result: object | None = None

    async def save_apply_result(self, result: object, applied_by: str) -> None:
        _ = applied_by
        self.saved_result = result

    async def save_topic_metadata(self, name: str, metadata: dict[str, object]) -> None:
        _ = name
        _ = metadata

    async def delete_topic_metadata(self, name: str) -> None:
        _ = name


class _TopicAuditRepository:
    def __init__(self) -> None:
        self.entries: list[dict[str, object]] = []

    async def log_topic_operation(self, **kwargs: object) -> str:
        self.entries.append(kwargs)
        return "audit-topic"


class _TopicPolicyRepository:
    async def list_policies(self, policy_type=None, status=None) -> list[object]:
        _ = policy_type
        _ = status
        return []


class _FakeTopicAdapter:
    def __init__(self) -> None:
        self.create_calls = 0
        self.delete_calls = 0
        self.partition_calls = 0
        self.config_calls = 0

    async def describe_topics(self, names: list[str]) -> dict[str, dict[str, object]]:
        return {
            name: {
                "partition_count": 3,
                "replication_factor": 1,
                "config": {"cleanup.policy": "delete"},
            }
            for name in names
        }

    async def create_topics(self, specs: list[object]) -> dict[str, Exception | None]:
        self.create_calls += 1
        _ = specs
        return {}

    async def delete_topics(self, names: list[str]) -> dict[str, Exception | None]:
        self.delete_calls += 1
        _ = names
        return {}

    async def create_partitions(self, partitions: dict[str, int]) -> dict[str, Exception | None]:
        self.partition_calls += 1
        _ = partitions
        return {}

    async def alter_topic_configs(
        self, configs: dict[str, dict[str, str]]
    ) -> dict[str, Exception | None]:
        self.config_calls += 1
        _ = configs
        return {}


class _SchemaConnectionManager:
    kafka_cluster_repo = None
    schema_registry_repo = None

    async def get_schema_registry_client(self, registry_id: str) -> object:
        _ = registry_id
        return object()


class _SchemaMetadataRepository:
    def __init__(self) -> None:
        self.saved_result: object | None = None
        self.saved_plan: DomainSchemaPlan | None = None
        self.saved_plan_actor: str | None = None

    async def save_apply_result(self, result: object, applied_by: str) -> None:
        _ = applied_by
        self.saved_result = result

    async def save_plan(self, plan: DomainSchemaPlan, created_by: str) -> None:
        self.saved_plan = plan
        self.saved_plan_actor = created_by

    async def record_artifact(self, artifact: object, change_id: str) -> None:
        _ = artifact
        _ = change_id


class _SchemaAuditRepository:
    def __init__(self) -> None:
        self.entries: list[dict[str, object]] = []

    async def log_operation(self, **kwargs: object) -> str:
        self.entries.append(kwargs)
        return "audit-schema"


class _SchemaPolicyRepository:
    async def list_active_policies(self, env: str) -> list[object]:
        _ = env
        return []


class _FakeSchemaRegistryAdapter:
    def __init__(self, schema_text: str) -> None:
        self.schema_text = schema_text
        self.register_calls = 0

    async def describe_subjects(self, subjects) -> dict[str, SchemaVersionInfo]:
        return {
            subject: SchemaVersionInfo(
                version=1,
                schema_id=101,
                schema=self.schema_text,
                schema_type="AVRO",
                references=[],
                hash="hash-001",
            )
            for subject in subjects
        }

    async def check_compatibility(self, spec, references=None) -> DomainSchemaCompatibilityReport:
        _ = references
        return DomainSchemaCompatibilityReport(
            subject=spec.subject,
            mode=spec.compatibility,
            is_compatible=True,
            issues=(),
        )

    async def register_schema(self, spec, compatibility: bool = True) -> tuple[int, int]:
        _ = spec
        _ = compatibility
        self.register_calls += 1
        return (2, 202)


@pytest.mark.asyncio
async def test_topic_apply_uses_evaluated_plan_and_skips_noop_topics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = _FakeTopicAdapter()
    monkeypatch.setattr(topic_apply_module, "KafkaTopicAdapter", lambda admin_client: adapter)

    metadata_repository = _TopicMetadataRepository()
    audit_repository = _TopicAuditRepository()
    use_case = TopicBatchApplyUseCase(
        connection_manager=cast(IConnectionManager, cast(object, _TopicConnectionManager())),
        metadata_repository=cast(ITopicMetadataRepository, cast(object, metadata_repository)),
        audit_repository=cast(IAuditRepository, cast(object, audit_repository)),
        policy_repository=cast(IPolicyRepository, cast(object, _TopicPolicyRepository())),
    )

    batch = DomainTopicBatch(
        change_id="chg-topic-noop-001",
        env=TopicEnvironment.DEV,
        specs=(
            DomainTopicSpec(
                name="dev.orders.created",
                action=DomainTopicAction.UPDATE,
                config=DomainTopicConfig(
                    partitions=3,
                    replication_factor=1,
                    cleanup_policy=DomainCleanupPolicy.DELETE,
                ),
                metadata=DomainTopicMetadata(
                    owners=("team-platform",),
                    doc="https://docs.example.com/topic",
                ),
            ),
        ),
    )

    result = await use_case.execute("cluster-a", batch, "tester")

    assert result.applied == ()
    assert result.skipped == ("dev.orders.created",)
    assert result.failed == ()
    assert result.summary() == {
        "total_items": 1,
        "planned_count": 0,
        "applied_count": 0,
        "skipped_count": 1,
        "failed_count": 0,
        "warning_count": 0,
    }
    assert adapter.create_calls == 0
    assert adapter.delete_calls == 0
    assert adapter.partition_calls == 0
    assert adapter.config_calls == 0
    assert metadata_repository.saved_result == result
    assert audit_repository.entries[-1]["status"] == AuditStatus.COMPLETED


@pytest.mark.asyncio
async def test_schema_apply_uses_evaluated_plan_and_skips_noop_subjects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    schema_text = json.dumps(
        {
            "type": "record",
            "name": "OrderCreated",
            "fields": [{"name": "id", "type": "string"}],
        }
    )
    adapter = _FakeSchemaRegistryAdapter(schema_text)
    monkeypatch.setattr(
        schema_apply_module,
        "ConfluentSchemaRegistryAdapter",
        lambda registry_client: adapter,
    )

    metadata_repository = _SchemaMetadataRepository()
    audit_repository = _SchemaAuditRepository()
    use_case = SchemaBatchApplyUseCase(
        connection_manager=cast(IConnectionManager, cast(object, _SchemaConnectionManager())),
        metadata_repository=cast(ISchemaMetadataRepository, cast(object, metadata_repository)),
        audit_repository=cast(ISchemaAuditRepository, cast(object, audit_repository)),
        policy_repository=cast(ISchemaPolicyRepository, cast(object, _SchemaPolicyRepository())),
    )

    batch = DomainSchemaBatch(
        change_id="chg-schema-noop-001",
        env=SchemaEnvironment.DEV,
        subject_strategy=DomainSubjectStrategy.TOPIC_NAME,
        specs=(
            DomainSchemaSpec(
                subject="dev.orders.created-value",
                schema_type=DomainSchemaType.AVRO,
                compatibility=DomainCompatibilityMode.BACKWARD,
                schema=schema_text,
                metadata=DomainSchemaMetadata(
                    owner="team-platform",
                    doc="https://docs.example.com/schema",
                ),
            ),
        ),
    )

    result = await use_case.execute("registry-a", "storage-a", batch, "tester")

    assert result.registered == ()
    assert result.skipped == ("dev.orders.created-value",)
    assert result.failed == ()
    assert result.summary() == {
        "total_items": 1,
        "planned_count": 0,
        "registered_count": 0,
        "skipped_count": 1,
        "failed_count": 0,
        "warning_count": 0,
    }
    assert adapter.register_calls == 0
    assert metadata_repository.saved_result == result
    assert audit_repository.entries[-1]["status"] == AuditStatus.COMPLETED


@pytest.mark.asyncio
async def test_schema_apply_persists_plan_for_history_reason_recovery(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    schema_text = json.dumps(
        {
            "type": "record",
            "name": "OrderCreated",
            "fields": [{"name": "id", "type": "string"}],
        }
    )
    adapter = _FakeSchemaRegistryAdapter(schema_text)
    monkeypatch.setattr(
        schema_apply_module,
        "ConfluentSchemaRegistryAdapter",
        lambda registry_client: adapter,
    )

    metadata_repository = _SchemaMetadataRepository()
    audit_repository = _SchemaAuditRepository()
    use_case = SchemaBatchApplyUseCase(
        connection_manager=cast(IConnectionManager, cast(object, _SchemaConnectionManager())),
        metadata_repository=cast(ISchemaMetadataRepository, cast(object, metadata_repository)),
        audit_repository=cast(ISchemaAuditRepository, cast(object, audit_repository)),
        policy_repository=cast(ISchemaPolicyRepository, cast(object, _SchemaPolicyRepository())),
    )

    batch = DomainSchemaBatch(
        change_id="chg-schema-reason-history-001",
        env=SchemaEnvironment.DEV,
        subject_strategy=DomainSubjectStrategy.TOPIC_NAME,
        specs=(
            DomainSchemaSpec(
                subject="dev.orders.created-value",
                schema_type=DomainSchemaType.AVRO,
                compatibility=DomainCompatibilityMode.BACKWARD,
                schema=schema_text,
                metadata=DomainSchemaMetadata(
                    owner="team-platform",
                    doc="https://docs.example.com/schema",
                ),
                reason="document the order schema rollout",
            ),
        ),
    )

    _ = await use_case.execute("registry-a", "storage-a", batch, "tester")

    saved_plan = cast(DomainSchemaPlan, metadata_repository.saved_plan)
    assert saved_plan is not None
    assert metadata_repository.saved_plan_actor == "tester"
    assert saved_plan.items[0].reason == "document the order schema rollout"
