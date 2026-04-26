from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

import pytest

import app.schema.application.use_cases.governance.drift as drift_module
from app.schema.application.use_cases.governance.drift import GetSchemaDriftUseCase
from app.schema.domain.models import SchemaVersionInfo


class _FakeSession:
    async def scalar(self, _statement):
        return None


@dataclass
class _FakeMetadataRepository:
    @asynccontextmanager
    async def session_factory(self) -> AsyncIterator[_FakeSession]:
        yield _FakeSession()


@dataclass
class _FakeConnectionManager:
    async def get_schema_registry_client(self, registry_id: str) -> object:
        assert registry_id == "registry-1"
        return object()


class _FakeRegistryAdapter:
    def __init__(self, client: object) -> None:
        self.client = client

    async def get_schema_versions(self, subject: str) -> list[int]:
        assert subject == "dev.orders-value"
        return [1, 2]

    async def get_schema_by_version(self, subject: str, version: int) -> SchemaVersionInfo:
        assert subject == "dev.orders-value"
        assert version == 2
        return SchemaVersionInfo(
            version=2,
            schema_id=102,
            schema='{"type":"record","name":"Order","fields":[{"name":"id","type":"string"},{"name":"status","type":["null","string"],"default":null}]}',
            schema_type="AVRO",
            references=[],
            hash="hash-2",
            canonical_hash="canonical-2",
        )


@pytest.mark.asyncio
async def test_drift_use_case_uses_highest_live_version(monkeypatch) -> None:
    monkeypatch.setattr(drift_module, "ConfluentSchemaRegistryAdapter", _FakeRegistryAdapter)
    use_case = GetSchemaDriftUseCase(
        connection_manager=_FakeConnectionManager(),  # type: ignore[arg-type]
        metadata_repository=_FakeMetadataRepository(),  # type: ignore[arg-type]
    )

    result = await use_case.execute(registry_id="registry-1", subject="dev.orders-value")

    assert result.subject == "dev.orders-value"
    assert result.registry_latest_version == 2
    assert result.registry_canonical_hash == "canonical-2"
    assert result.catalog_latest_version is None
    assert "catalog_subject_missing" in result.drift_flags
