"""Schema version retrieval and export use cases."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from typing import Protocol, cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.kafka.connection_manager import IConnectionManager
from app.infra.kafka.schema_registry_adapter import ConfluentSchemaRegistryAdapter
from app.schema.domain.models import (
    DomainCompatibilityMode,
    DomainSchemaSpec,
    DomainSchemaType,
    SchemaVersionExport,
    SchemaVersionInfo,
    SubjectName,
    SubjectVersionComparison,
    SubjectVersionDetail,
    SubjectVersionList,
    SubjectVersionSummary,
)
from app.schema.domain.repositories.interfaces import ISchemaMetadataRepository
from app.schema.domain.services import SchemaPlannerService, _normalize_schema_text
from app.schema.infrastructure.models import (
    SchemaArtifactModel,
    SchemaAuditLogModel,
    SchemaMetadataModel,
    SchemaPlanModel,
)


class _MetadataRepositoryWithSessionFactory(Protocol):
    session_factory: Callable[[], AbstractAsyncContextManager[AsyncSession]]


@dataclass(slots=True)
class _VersionContext:
    artifact_by_version: dict[int, SchemaArtifactModel]
    audit_logs: dict[str, str]
    plan_reasons: dict[tuple[str, str], str]
    owner: str | None
    doc: str | None
    tags: list[str]
    compatibility_mode: str | None


def _parse_compatibility_mode(
    tags_payload: dict[str, object] | None,
) -> str | None:
    raw_mode = tags_payload.get("compatibility_mode") if tags_payload else None
    if isinstance(raw_mode, str):
        mode = raw_mode.strip()
        if mode:
            return mode
    return None


def _parse_tags(tags_payload: dict[str, object] | None) -> list[str]:
    if not tags_payload:
        return []
    raw_items = tags_payload.get("items")
    if not isinstance(raw_items, list):
        return []
    return [item.strip() for item in raw_items if isinstance(item, str) and item.strip()]


def _build_export_filename(subject: str, version: int, schema_type: str) -> tuple[str, str]:
    schema_type_upper = schema_type.upper()
    if schema_type_upper == "PROTOBUF":
        return f"{subject}.v{version}.proto", "text/plain; charset=utf-8"
    if schema_type_upper == "JSON":
        return f"{subject}.v{version}.json", "application/json"
    return f"{subject}.v{version}.avsc", "application/json"


class _BaseSchemaVersionUseCase:
    def __init__(
        self,
        connection_manager: IConnectionManager,
        metadata_repository: ISchemaMetadataRepository,
    ) -> None:
        self.connection_manager = connection_manager
        self.metadata_repository = metadata_repository

    async def _get_registry_repository(self, registry_id: str) -> ConfluentSchemaRegistryAdapter:
        registry_client = await self.connection_manager.get_schema_registry_client(registry_id)
        return ConfluentSchemaRegistryAdapter(registry_client)

    async def _ensure_subject_exists(
        self,
        registry_repository: ConfluentSchemaRegistryAdapter,
        subject: SubjectName,
    ) -> SchemaVersionInfo:
        describe_result = await registry_repository.describe_subjects([subject])
        current_info = describe_result.get(subject)
        if current_info is None or current_info.version is None:
            raise ValueError(f"Subject '{subject}' not found")
        return current_info

    async def _load_context(self, subject: SubjectName) -> _VersionContext:
        metadata_repository = cast(
            _MetadataRepositoryWithSessionFactory,
            cast(object, self.metadata_repository),
        )
        async with metadata_repository.session_factory() as session:
            result_artifacts = await session.execute(
                select(SchemaArtifactModel).where(SchemaArtifactModel.subject == subject)
            )
            artifact_models = result_artifacts.scalars().all()
            artifact_by_version = {
                artifact.version: artifact
                for artifact in artifact_models
                if artifact.version is not None
            }
            change_ids = {artifact.change_id for artifact in artifact_models if artifact.change_id}

            audit_logs: dict[str, str] = {}
            plan_reasons: dict[tuple[str, str], str] = {}

            if change_ids:
                result_audit = await session.execute(
                    select(SchemaAuditLogModel).where(SchemaAuditLogModel.change_id.in_(change_ids))
                )
                audit_logs = {log.change_id: log.actor for log in result_audit.scalars().all()}

                result_plan = await session.execute(
                    select(SchemaPlanModel).where(SchemaPlanModel.change_id.in_(change_ids))
                )
                for plan_model in result_plan.scalars().all():
                    items = plan_model.plan_data.get("items", []) if plan_model.plan_data else []
                    for item in items:
                        item_subject = item.get("subject")
                        reason = item.get("reason")
                        if isinstance(item_subject, str) and isinstance(reason, str) and reason:
                            plan_reasons[(plan_model.change_id, item_subject)] = reason

            result_metadata = await session.execute(
                select(SchemaMetadataModel).where(SchemaMetadataModel.subject == subject)
            )
            metadata_model = result_metadata.scalar_one_or_none()

        return _VersionContext(
            artifact_by_version=artifact_by_version,
            audit_logs=audit_logs,
            plan_reasons=plan_reasons,
            owner=metadata_model.owner if metadata_model is not None else None,
            doc=metadata_model.doc if metadata_model is not None else None,
            tags=_parse_tags(metadata_model.tags if metadata_model is not None else None),
            compatibility_mode=_parse_compatibility_mode(
                metadata_model.tags if metadata_model is not None else None
            ),
        )

    def _build_version_summary(
        self,
        *,
        subject: SubjectName,
        version_info: SchemaVersionInfo,
        context: _VersionContext,
    ) -> SubjectVersionSummary:
        if version_info.version is None or version_info.schema_id is None:
            raise ValueError(f"Version metadata for '{subject}' is incomplete")

        artifact_model = context.artifact_by_version.get(version_info.version)
        author = "system"
        commit_message = None
        if artifact_model is not None and artifact_model.change_id:
            author = context.audit_logs.get(artifact_model.change_id, "system")
            commit_message = context.plan_reasons.get((artifact_model.change_id, subject))

        return SubjectVersionSummary(
            version=version_info.version,
            schema_id=version_info.schema_id,
            schema_type=version_info.schema_type or "UNKNOWN",
            hash=version_info.hash,
            canonical_hash=version_info.canonical_hash,
            created_at=artifact_model.created_at.isoformat()
            if artifact_model is not None and artifact_model.created_at
            else None,
            author=author,
            commit_message=commit_message,
        )

    def _build_version_detail(
        self,
        *,
        subject: SubjectName,
        version_info: SchemaVersionInfo,
        context: _VersionContext,
    ) -> SubjectVersionDetail:
        summary = self._build_version_summary(
            subject=subject,
            version_info=version_info,
            context=context,
        )
        return SubjectVersionDetail(
            subject=subject,
            version=summary.version,
            schema_id=summary.schema_id,
            schema_str=version_info.schema or "",
            schema_type=summary.schema_type,
            hash=summary.hash,
            canonical_hash=summary.canonical_hash,
            references=[reference.to_dict() for reference in version_info.references],
            owner=context.owner,
            compatibility_mode=context.compatibility_mode,
            created_at=summary.created_at,
            author=summary.author,
            commit_message=summary.commit_message,
        )


class GetSchemaVersionsUseCase(_BaseSchemaVersionUseCase):
    """Public subject-version listing use case."""

    async def execute(self, registry_id: str, subject: SubjectName) -> SubjectVersionList:
        registry_repository = await self._get_registry_repository(registry_id)
        await self._ensure_subject_exists(registry_repository, subject)
        versions = await registry_repository.get_schema_versions(subject)
        version_infos = await asyncio.gather(
            *(registry_repository.get_schema_by_version(subject, version) for version in versions)
        )
        context = await self._load_context(subject)
        summaries = [
            self._build_version_summary(
                subject=subject,
                version_info=version_info,
                context=context,
            )
            for version_info in version_infos
            if version_info.version is not None and version_info.schema_id is not None
        ]
        return SubjectVersionList(
            subject=subject,
            versions=sorted(summaries, key=lambda item: item.version, reverse=True),
        )


class GetSchemaVersionUseCase(_BaseSchemaVersionUseCase):
    """Public exact schema-version retrieval use case."""

    async def execute(
        self,
        registry_id: str,
        subject: SubjectName,
        version: int,
    ) -> SubjectVersionDetail:
        registry_repository = await self._get_registry_repository(registry_id)
        await self._ensure_subject_exists(registry_repository, subject)
        versions = await registry_repository.get_schema_versions(subject)
        if version not in versions:
            raise ValueError(f"Version {version} for subject '{subject}' not found")

        version_info = await registry_repository.get_schema_by_version(subject, version)
        context = await self._load_context(subject)
        return self._build_version_detail(
            subject=subject,
            version_info=version_info,
            context=context,
        )


class ExportSchemaVersionUseCase:
    """Schema export use case for latest or exact version."""

    def __init__(self, version_use_case: GetSchemaVersionUseCase) -> None:
        self.version_use_case = version_use_case

    async def execute(
        self,
        registry_id: str,
        subject: SubjectName,
        version: int,
    ) -> SchemaVersionExport:
        detail = await self.version_use_case.execute(
            registry_id=registry_id,
            subject=subject,
            version=version,
        )
        filename, media_type = _build_export_filename(
            detail.subject,
            detail.version,
            detail.schema_type,
        )
        return SchemaVersionExport(
            subject=detail.subject,
            version=detail.version,
            schema_type=detail.schema_type,
            filename=filename,
            media_type=media_type,
            schema_str=detail.schema_str,
        )

    async def execute_latest(self, registry_id: str, subject: SubjectName) -> SchemaVersionExport:
        registry_repository = await self.version_use_case._get_registry_repository(registry_id)
        latest_info = await self.version_use_case._ensure_subject_exists(
            registry_repository, subject
        )
        if latest_info.version is None:
            raise ValueError(f"Subject '{subject}' not found")
        version_list = await self.version_use_case.execute(
            registry_id=registry_id,
            subject=subject,
            version=latest_info.version,
        )
        filename, media_type = _build_export_filename(
            version_list.subject,
            version_list.version,
            version_list.schema_type,
        )
        return SchemaVersionExport(
            subject=version_list.subject,
            version=version_list.version,
            schema_type=version_list.schema_type,
            filename=filename,
            media_type=media_type,
            schema_str=version_list.schema_str,
        )


class CompareSchemaVersionsUseCase(_BaseSchemaVersionUseCase):
    """Compare two versions of the same subject."""

    async def execute(
        self,
        registry_id: str,
        subject: SubjectName,
        from_version: int,
        to_version: int,
    ) -> SubjectVersionComparison:
        registry_repository = await self._get_registry_repository(registry_id)
        await self._ensure_subject_exists(registry_repository, subject)

        available_versions = await registry_repository.get_schema_versions(subject)
        if from_version not in available_versions:
            raise ValueError(f"Version {from_version} for subject '{subject}' not found")
        if to_version not in available_versions:
            raise ValueError(f"Version {to_version} for subject '{subject}' not found")

        from_info, to_info = await asyncio.gather(
            registry_repository.get_schema_by_version(subject, from_version),
            registry_repository.get_schema_by_version(subject, to_version),
        )

        schema_type = to_info.schema_type or from_info.schema_type or DomainSchemaType.AVRO.value
        context = await self._load_context(subject)
        compatibility_mode = DomainCompatibilityMode.NONE
        if context.compatibility_mode:
            try:
                compatibility_mode = DomainCompatibilityMode(context.compatibility_mode)
            except ValueError:
                compatibility_mode = DomainCompatibilityMode.NONE

        planner = SchemaPlannerService(registry_repository)
        try:
            resolved_schema_type = DomainSchemaType(schema_type)
        except ValueError:
            resolved_schema_type = DomainSchemaType.AVRO
        spec = DomainSchemaSpec(
            subject=subject,
            schema_type=resolved_schema_type,
            compatibility=compatibility_mode,
            schema=to_info.schema or "",
        )

        changed = _normalize_schema_text(from_info.schema, schema_type) != _normalize_schema_text(
            to_info.schema,
            schema_type,
        )
        if changed:
            diff = planner._calculate_schema_diff(from_info, spec)
            diff_type = diff.type
            changes = list(diff.changes)
        else:
            diff_type = "no_change"
            changes = ["No schema change detected"]

        return SubjectVersionComparison(
            subject=subject,
            from_version=from_version,
            to_version=to_version,
            changed=changed,
            diff_type=diff_type,
            changes=changes,
            schema_type=schema_type,
            compatibility_mode=context.compatibility_mode,
            from_schema=from_info.schema,
            to_schema=to_info.schema,
        )
