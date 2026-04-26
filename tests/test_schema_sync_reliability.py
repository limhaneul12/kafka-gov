from __future__ import annotations

from dataclasses import dataclass, field

import pytest

import app.schema.application.use_cases.management.sync as sync_module
from app.schema.application.use_cases.management.sync import SchemaSyncUseCase
from app.schema.domain.models import SchemaVersionInfo


@dataclass
class _FakeConnectionManager:
    async def get_schema_registry_client(self, registry_id: str) -> object:
        assert registry_id == "registry-1"
        return object()


@dataclass
class _FakeMetadataRepository:
    metadata_payloads: list[dict[str, object]] = field(default_factory=list)

    async def record_artifact(self, artifact, change_id) -> None:
        return None

    async def save_schema_metadata(self, subject: str, metadata: dict[str, object]) -> None:
        self.metadata_payloads.append({"subject": subject, **metadata})


@dataclass
class _FakeAuditRepository:
    async def log_operation(self, **kwargs) -> str:
        return "audit-id"


class _FakeRegistryAdapter:
    def __init__(self, client: object) -> None:
        self.client = client

    async def list_all_subjects(self) -> list[str]:
        return ["dev.orders-value"]

    async def describe_subjects(self, subjects) -> dict[str, SchemaVersionInfo]:
        return {
            "dev.orders-value": SchemaVersionInfo(
                version=3,
                schema_id=100,
                schema='{"type":"record","name":"Order","fields":[]}',
                schema_type="AVRO",
                references=[],
                hash="hash-1",
                canonical_hash="canonical-1",
            )
        }


@pytest.mark.asyncio
async def test_sync_does_not_inject_placeholder_owner_or_compatibility(monkeypatch) -> None:
    metadata_repository = _FakeMetadataRepository()
    use_case = SchemaSyncUseCase(
        connection_manager=_FakeConnectionManager(),
        metadata_repository=metadata_repository,  # type: ignore[arg-type]
        audit_repository=_FakeAuditRepository(),  # type: ignore[arg-type]
        session_factory=None,
    )
    monkeypatch.setattr(sync_module, "ConfluentSchemaRegistryAdapter", _FakeRegistryAdapter)

    result = await use_case.execute(
        registry_id="registry-1",
        actor="alice",
    )

    assert result["total"] == 1
    assert metadata_repository.metadata_payloads == [
        {
            "subject": "dev.orders-value",
            "created_by": "alice",
            "updated_by": "alice",
        }
    ]
