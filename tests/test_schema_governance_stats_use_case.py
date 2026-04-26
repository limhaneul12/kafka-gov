from __future__ import annotations

from dataclasses import dataclass

import pytest

import app.schema.application.use_cases.governance.stats as stats_module
from app.schema.application.use_cases.governance.stats import GetGovernanceStatsUseCase
from app.schema.domain.models import (
    DomainCompatibilityMode,
    DomainSchemaArtifact,
    DomainSchemaType,
    SchemaVersionInfo,
)


@dataclass
class _FailingConnectionManager:
    async def get_schema_registry_client(self, registry_id: str) -> object:
        raise RuntimeError(registry_id)


@dataclass
class _FakeConnectionManager:
    async def get_schema_registry_client(self, registry_id: str) -> object:
        assert registry_id == "registry-1"
        return object()


@dataclass
class _FakeMetadataRepository:
    async def list_artifacts(self) -> list[DomainSchemaArtifact]:
        return [
            DomainSchemaArtifact(
                subject="prod.orders-value",
                storage_url="registry://prod.orders-value/versions/3",
                version=3,
                schema_type=DomainSchemaType.AVRO,
                compatibility_mode=DomainCompatibilityMode.FULL,
                owner="team-orders",
            )
        ]


@dataclass
class _FakePolicyRepository:
    async def list_active_policies(self, env: str) -> list[object]:
        assert env == "total"
        return []


class _FakeRegistryAdapter:
    def __init__(self, client: object) -> None:
        self.client = client

    async def list_all_subjects(self) -> list[str]:
        return ["prod.orders-value"]

    async def describe_subjects(self, subjects: list[str]) -> dict[str, SchemaVersionInfo]:
        return {
            subject: SchemaVersionInfo(
                version=3,
                schema_id=301,
                schema='{"type":"record","name":"Order","fields":[{"name":"id","type":"string"}]}',
                schema_type="AVRO",
                references=[],
                hash=f"hash-{subject}",
                canonical_hash=f"canonical-{subject}",
            )
            for subject in subjects
        }


@pytest.mark.asyncio
async def test_governance_stats_returns_empty_dashboard_when_registry_unavailable() -> None:
    use_case = GetGovernanceStatsUseCase(
        connection_manager=_FailingConnectionManager(),  # type: ignore[arg-type]
        metadata_repository=_FakeMetadataRepository(),  # type: ignore[arg-type]
    )

    result = await use_case.execute("registry-1")

    assert result.total_subjects == 0
    assert result.top_subjects == []
    assert result.scores.total_score == 0.0


@pytest.mark.asyncio
async def test_governance_stats_uses_metadata_and_live_subjects(monkeypatch) -> None:
    monkeypatch.setattr(stats_module, "ConfluentSchemaRegistryAdapter", _FakeRegistryAdapter)
    use_case = GetGovernanceStatsUseCase(
        connection_manager=_FakeConnectionManager(),  # type: ignore[arg-type]
        metadata_repository=_FakeMetadataRepository(),  # type: ignore[arg-type]
        policy_repository=_FakePolicyRepository(),  # type: ignore[arg-type]
    )

    result = await use_case.execute("registry-1")

    assert result.total_subjects == 1
    assert result.total_versions == 3
    assert result.orphan_subjects == 0
    assert result.top_subjects[0].subject == "prod.orders-value"
    assert result.top_subjects[0].owner == "team-orders"
    assert result.top_subjects[0].compatibility_mode == "FULL"
