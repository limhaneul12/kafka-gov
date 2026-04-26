from __future__ import annotations

from collections.abc import AsyncGenerator
from pathlib import Path

import pytest

from app.schema.application.services.catalog_sync import CatalogSyncService
from app.schema.infrastructure.catalog_models import SchemaSubjectModel, SchemaVersionModel
from app.schema.infrastructure.models import SchemaArtifactModel, SchemaMetadataModel
from app.shared.database import DatabaseManager


class _FakeSchemaRegistryClient:
    async def get_subjects(self) -> list[str]:
        return []


@pytest.fixture
async def database_manager(tmp_path: Path) -> AsyncGenerator[DatabaseManager, None]:
    db_path = tmp_path / "catalog_sync.db"
    manager = DatabaseManager(f"sqlite+aiosqlite:///{db_path}")
    await manager.initialize()
    await manager.create_tables()
    try:
        yield manager
    finally:
        await manager.close()


@pytest.mark.asyncio
async def test_catalog_sync_removes_stale_subject_metadata(
    database_manager: DatabaseManager,
) -> None:
    async with database_manager.get_db_session() as session:
        session.add(
            SchemaSubjectModel(
                subject="dev.orders-value",
                latest_version=2,
                compat_level="FULL",
                mode_readonly=False,
                env="dev",
                owner_team="team-orders",
                pii_score=0.0,
                risk_score=0.0,
            )
        )
        session.add(
            SchemaVersionModel(
                subject="dev.orders-value",
                version=2,
                schema_type="AVRO",
                schema_id=201,
                schema_str='{"type":"record","name":"Order","fields":[]}',
                schema_canonical_hash="canonical-201",
                references=None,
                rule_set=None,
                sr_metadata=None,
                fields_meta=None,
                lint_report=None,
            )
        )
        session.add(
            SchemaArtifactModel(
                subject="dev.orders-value",
                version=2,
                storage_url="registry://dev.orders-value/versions/2",
                checksum="checksum-201",
                change_id="chg-201",
                schema_type="AVRO",
                file_size=128,
            )
        )
        session.add(
            SchemaMetadataModel(
                subject="dev.orders-value",
                owner="team-orders",
                doc="https://docs.example/orders",
                tags={"items": ["golden"], "compatibility_mode": "FULL"},
                description="order schema",
                created_by="alice",
                updated_by="alice",
            )
        )

    async with database_manager.get_db_session() as session:
        service = CatalogSyncService(sr_client=_FakeSchemaRegistryClient(), session=session)
        metrics = await service.sync_all()

    async with database_manager.get_db_session() as session:
        assert await session.get(SchemaSubjectModel, "dev.orders-value") is None
        assert await session.get(SchemaMetadataModel, "dev.orders-value") is None
        assert await session.get(SchemaVersionModel, ("dev.orders-value", 2)) is None
        assert await session.get(SchemaArtifactModel, ("dev.orders-value", 2)) is None

    assert metrics.subjects_total == 0
    assert metrics.subjects_removed == 1
    assert metrics.versions_removed == 1
    assert metrics.artifacts_removed == 1
    assert metrics.metadata_removed == 1
