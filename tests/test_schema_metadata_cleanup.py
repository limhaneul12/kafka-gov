from __future__ import annotations

from collections.abc import AsyncGenerator
from pathlib import Path

import pytest

from app.schema.infrastructure.repository.mysql_repository import (
    MySQLSchemaMetadataRepository,
)
from app.shared.database import DatabaseManager


@pytest.fixture
async def metadata_repository(
    tmp_path: Path,
) -> AsyncGenerator[MySQLSchemaMetadataRepository, None]:
    db_path = tmp_path / "schema_metadata_cleanup.db"
    manager = DatabaseManager(f"sqlite+aiosqlite:///{db_path}")
    await manager.initialize()
    await manager.create_tables()
    try:
        yield MySQLSchemaMetadataRepository(session_factory=manager.get_db_session)
    finally:
        await manager.close()


@pytest.mark.asyncio
async def test_save_schema_metadata_ignores_placeholder_owner_and_compatibility(
    metadata_repository: MySQLSchemaMetadataRepository,
) -> None:
    await metadata_repository.save_schema_metadata(
        "dev.orders-value",
        {
            "owner": "team-orders-placeholder",
            "compatibility_mode": "compatibility-placeholder",
            "created_by": "alice",
            "updated_by": "alice",
        },
    )

    metadata = await metadata_repository.get_schema_metadata("dev.orders-value")
    artifacts, total = await metadata_repository.search_artifacts(query="orders", limit=10)

    assert metadata is not None
    assert metadata["owner"] is None
    assert metadata["compatibility_mode"] is None
    assert total == 1
    assert artifacts[0].owner is None
    assert artifacts[0].compatibility_mode is None


@pytest.mark.asyncio
async def test_sync_style_metadata_update_clears_existing_placeholder_owner(
    metadata_repository: MySQLSchemaMetadataRepository,
) -> None:
    await metadata_repository.save_schema_metadata(
        "dev.orders-value",
        {
            "owner": "legacy-placeholder",
            "compatibility_mode": "BACKWARD",
            "created_by": "alice",
            "updated_by": "alice",
        },
    )

    await metadata_repository.save_schema_metadata(
        "dev.orders-value",
        {
            "updated_by": "sync-bot",
        },
    )

    metadata = await metadata_repository.get_schema_metadata("dev.orders-value")

    assert metadata is not None
    assert metadata["owner"] is None
    assert metadata["compatibility_mode"] == "BACKWARD"
