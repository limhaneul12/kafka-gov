"""Schema drift reporting use case."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from typing import Protocol, cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.kafka.connection_manager import IConnectionManager
from app.infra.kafka.schema_registry_adapter import ConfluentSchemaRegistryAdapter
from app.schema.domain.models import SubjectDriftReport, SubjectName
from app.schema.domain.repositories.interfaces import ISchemaMetadataRepository
from app.schema.infrastructure.catalog_models import (
    ObservedUsageModel,
    SchemaSubjectModel,
    SchemaVersionModel,
)


class _MetadataRepositoryWithSessionFactory(Protocol):
    session_factory: Callable[[], AbstractAsyncContextManager[AsyncSession]]


class GetSchemaDriftUseCase:
    """Compare live registry latest state with local catalog snapshots."""

    def __init__(
        self,
        connection_manager: IConnectionManager,
        metadata_repository: ISchemaMetadataRepository,
    ) -> None:
        self.connection_manager = connection_manager
        self.metadata_repository = metadata_repository

    async def execute(self, registry_id: str, subject: SubjectName) -> SubjectDriftReport:
        registry_client = await self.connection_manager.get_schema_registry_client(registry_id)
        registry_repository = ConfluentSchemaRegistryAdapter(registry_client)

        versions = await registry_repository.get_schema_versions(subject)
        if not versions:
            raise ValueError(f"Subject '{subject}' not found")
        latest_version = max(versions)
        current_info = await registry_repository.get_schema_by_version(subject, latest_version)
        if current_info.version is None:
            raise ValueError(f"Subject '{subject}' not found")

        metadata_repository = cast(
            _MetadataRepositoryWithSessionFactory,
            cast(object, self.metadata_repository),
        )
        async with metadata_repository.session_factory() as session:
            subject_row = await session.scalar(
                select(SchemaSubjectModel).where(SchemaSubjectModel.subject == subject)
            )
            version_row = await session.scalar(
                select(SchemaVersionModel)
                .where(SchemaVersionModel.subject == subject)
                .order_by(SchemaVersionModel.version.desc())
                .limit(1)
            )
            observed_row = await session.scalar(
                select(ObservedUsageModel)
                .where(ObservedUsageModel.subject == subject)
                .order_by(ObservedUsageModel.version.desc(), ObservedUsageModel.last_seen_at.desc())
                .limit(1)
            )

        drift_flags: list[str] = []
        if subject_row is None:
            drift_flags.append("catalog_subject_missing")
        elif subject_row.latest_version != current_info.version:
            drift_flags.append("catalog_subject_version_mismatch")

        if version_row is None:
            drift_flags.append("catalog_version_missing")
        else:
            if version_row.version != current_info.version:
                drift_flags.append("catalog_snapshot_version_mismatch")
            if (
                current_info.canonical_hash is not None
                and version_row.schema_canonical_hash is not None
                and current_info.canonical_hash != version_row.schema_canonical_hash
            ):
                drift_flags.append("catalog_canonical_hash_mismatch")

        if observed_row is not None and observed_row.version != current_info.version:
            drift_flags.append("observed_usage_on_non_latest_version")

        return SubjectDriftReport(
            subject=subject,
            registry_latest_version=current_info.version,
            registry_canonical_hash=current_info.canonical_hash,
            catalog_latest_version=version_row.version if version_row is not None else None,
            catalog_canonical_hash=(
                version_row.schema_canonical_hash if version_row is not None else None
            ),
            observed_version=observed_row.version if observed_row is not None else None,
            last_synced_at=subject_row.updated_at.isoformat() if subject_row is not None else None,
            drift_flags=drift_flags,
            has_drift=bool(drift_flags),
        )
