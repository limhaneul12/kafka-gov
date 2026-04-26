from __future__ import annotations

from dataclasses import dataclass

import pytest

import app.schema.application.use_cases.governance.rollback as rollback_module
from app.schema.application.use_cases.governance.rollback import ExecuteRollbackSchemaUseCase
from app.schema.domain.models import (
    DomainCompatibilityMode,
    DomainSchemaApplyResult,
    SchemaVersionInfo,
)


@dataclass
class _FakeConnectionManager:
    async def get_schema_registry_client(self, registry_id: str) -> object:
        assert registry_id == "registry-1"
        return object()


@dataclass
class _FakeArtifact:
    compatibility_mode: DomainCompatibilityMode | None = DomainCompatibilityMode.BACKWARD
    storage_url: str | None = None
    owner: str | None = "team-order"


@dataclass
class _FakeMetadataRepository:
    deleted_subject: str | None = None
    deleted_after_version: int | None = None
    saved_result: DomainSchemaApplyResult | None = None

    async def get_latest_artifact(self, subject: str):
        assert subject == "prod.orders-value"
        return _FakeArtifact()

    async def delete_artifacts_newer_than(self, subject: str, version: int) -> None:
        self.deleted_subject = subject
        self.deleted_after_version = version

    async def save_apply_result(self, result: DomainSchemaApplyResult, applied_by: str) -> None:
        assert applied_by == "alice"
        self.saved_result = result


@dataclass
class _UnusedApplyUseCase:
    pass


class _FakeRegistryAdapter:
    def __init__(self, client: object) -> None:
        self.client = client
        self.deleted_versions: list[int] = []

    async def get_schema_by_version(self, subject: str, version: int) -> SchemaVersionInfo:
        assert subject == "prod.orders-value"
        assert version == 1
        return SchemaVersionInfo(
            version=1,
            schema_id=10,
            schema='{"type":"record","name":"Order","fields":[]}',
            schema_type="AVRO",
            references=[],
            hash="hash-1",
            canonical_hash="canonical-1",
        )

    async def get_schema_versions(self, subject: str) -> list[int]:
        assert subject == "prod.orders-value"
        return [1, 2, 3]

    async def delete_version(self, subject: str, version: int) -> None:
        assert subject == "prod.orders-value"
        self.deleted_versions.append(version)


@pytest.mark.asyncio
async def test_execute_rollback_deletes_newer_versions_and_records_result(monkeypatch) -> None:
    metadata_repository = _FakeMetadataRepository()
    use_case = ExecuteRollbackSchemaUseCase(
        connection_manager=_FakeConnectionManager(),
        metadata_repository=metadata_repository,  # type: ignore[arg-type]
        apply_use_case=_UnusedApplyUseCase(),
    )
    adapter = _FakeRegistryAdapter(object())
    monkeypatch.setattr(
        rollback_module,
        "ConfluentSchemaRegistryAdapter",
        lambda client: adapter,
    )

    result = await use_case.execute(
        registry_id="registry-1",
        subject="prod.orders-value",
        version=1,
        actor="alice",
        reason="Rollback to v1",
    )

    assert result.registered == ("prod.orders-value",)
    assert result.skipped == ()
    assert result.artifacts[0].version == 1
    assert adapter.deleted_versions == [3, 2]
    assert metadata_repository.deleted_subject == "prod.orders-value"
    assert metadata_repository.deleted_after_version == 1
    assert metadata_repository.saved_result is not None
