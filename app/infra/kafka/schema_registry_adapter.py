from __future__ import annotations

import asyncio
import hashlib
from collections.abc import Iterable
from typing import Any, NoReturn, cast

import orjson
from confluent_kafka.schema_registry import AsyncSchemaRegistryClient, Schema, ServerConfig
from confluent_kafka.schema_registry.common.schema_registry_client import ConfigCompatibilityLevel
from confluent_kafka.schema_registry.error import SchemaRegistryError

from app.schema.domain.models import (
    CompatibilityResult,
    DescribeResult,
    DomainSchemaCompatibilityIssue,
    DomainSchemaCompatibilityReport,
    DomainSchemaSpec,
    Reference,
    SchemaVersionInfo,
    SubjectName,
)
from app.schema.domain.repositories.interfaces import ISchemaRegistryRepository
from app.schema.infrastructure.error_handlers import handle_schema_registry_error
from app.shared.logging_config import get_logger

logger = get_logger(__name__)


class ConfluentSchemaRegistryAdapter(ISchemaRegistryRepository):
    def __init__(self, client: AsyncSchemaRegistryClient) -> None:
        self.client: AsyncSchemaRegistryClient = client

    async def describe_subjects(self, subjects: Iterable[SubjectName]) -> DescribeResult:
        subject_list: list[SubjectName] = list(subjects)
        result: DescribeResult = {}
        all_subjects: list[str] = []

        try:
            all_subjects: list[str] = await self.client.get_subjects()
        except SchemaRegistryError as exc:
            self._raise_schema_registry_runtime_error("Describe subjects", exc)

        for subject in subject_list:
            if subject not in all_subjects:
                continue

            try:
                result[subject] = await self._get_latest_schema_version_info(subject)
            except SchemaRegistryError as e:
                logger.warning(
                    "schema_fetch_failed",
                    subject=subject,
                    error_type=e.__class__.__name__,
                    error_message=str(e),
                )
                continue

        return result

    async def check_compatibility(
        self,
        spec: DomainSchemaSpec,
        references: list[Reference] | None = None,
    ) -> DomainSchemaCompatibilityReport:
        try:
            schema_str: str = self._extract_schema_string(spec)
            schema_str = self._normalize_schema_string(schema_str)
            references_payload = cast(
                Any, [ref.to_dict() for ref in references] if references else []
            )

            schema_obj = Schema(
                schema_str=schema_str,
                schema_type=spec.schema_type.value
                if hasattr(spec.schema_type, "value")
                else spec.schema_type,
                references=references_payload,
            )

            is_compatible: bool = await self.client.test_compatibility(
                subject_name=spec.subject, schema=schema_obj
            )

            return DomainSchemaCompatibilityReport(
                subject=spec.subject,
                mode=spec.compatibility,
                is_compatible=is_compatible,
                issues=(),
            )
        except SchemaRegistryError as e:
            logger.warning(f"Compatibility check failed for {spec.subject}: {e}")
            issue = DomainSchemaCompatibilityIssue(
                path="$",
                message=str(e),
                issue_type="SCHEMA_REGISTRY_ERROR",
            )
            return DomainSchemaCompatibilityReport(
                subject=spec.subject,
                mode=spec.compatibility,
                is_compatible=False,
                issues=(issue,),
            )

    async def check_compatibility_batch(self, specs: list[DomainSchemaSpec]) -> CompatibilityResult:
        tasks = [
            self.check_compatibility(
                spec,
                [
                    Reference(name=ref.name, subject=ref.subject, version=ref.version)
                    for ref in spec.references
                ]
                if spec.references
                else None,
            )
            for spec in specs
        ]
        results_tuple = await asyncio.gather(*tasks, return_exceptions=True)
        results: list[DomainSchemaCompatibilityReport | BaseException] = list(results_tuple)

        compatibility_result: CompatibilityResult = {}
        for spec, result in zip(specs, results, strict=True):
            if isinstance(result, Exception):
                logger.error(f"Compatibility check failed for {spec.subject}: {result}")
                issue = DomainSchemaCompatibilityIssue(
                    path="$",
                    message=str(result),
                    issue_type="BATCH_CHECK_ERROR",
                )
                compatibility_result[spec.subject] = DomainSchemaCompatibilityReport(
                    subject=spec.subject,
                    mode=spec.compatibility,
                    is_compatible=False,
                    issues=(issue,),
                )
            elif isinstance(result, DomainSchemaCompatibilityReport):
                compatibility_result[spec.subject] = result

        return compatibility_result

    async def register_schema(
        self, spec: DomainSchemaSpec, compatibility: bool = True
    ) -> tuple[int, int]:
        try:
            schema_str: str = self._extract_schema_string(spec)
            schema_str = self._normalize_schema_string(schema_str)

            references_list: list[dict[str, int | str]] = [
                Reference(
                    name=ref.name,
                    subject=ref.subject,
                    version=ref.version,
                ).to_dict()
                for ref in spec.references
            ]
            references_payload = cast(Any, references_list)

            schema_obj = Schema(
                schema_str=schema_str,
                schema_type=spec.schema_type.value
                if hasattr(spec.schema_type, "value")
                else spec.schema_type,
                references=references_payload,
            )

            schema_id = await self.client.register_schema(
                subject_name=spec.subject,
                schema=schema_obj,
                normalize_schemas=True,
            )
            latest_version = await self._get_latest_schema_version_info(spec.subject)
            if latest_version.version is not None:
                logger.info(
                    f"Schema registered: {spec.subject} v{latest_version.version} (ID: {schema_id})"
                )
                return (latest_version.version, schema_id)

            logger.warning(f"Could not retrieve version for registered schema {spec.subject}")
            return (1, schema_id)
        except SchemaRegistryError as exc:
            self._raise_schema_registry_runtime_error("Schema registration", exc, spec.subject)

    async def delete_subject(self, subject: SubjectName) -> None:
        try:
            deleted_versions: list[int] = await self.client.delete_subject(subject)
            logger.info(f"Subject deleted: {subject} ({len(deleted_versions)} versions)")
        except SchemaRegistryError as exc:
            self._raise_schema_registry_runtime_error("Delete subject", exc, subject)

    async def delete_version(self, subject: SubjectName, version: int) -> None:
        try:
            deleted_version = await self.client.delete_version(subject, version)
            logger.info(f"Schema version deleted: {subject} v{deleted_version}")
        except SchemaRegistryError as exc:
            self._raise_schema_registry_runtime_error(
                "Delete schema version", exc, f"{subject} v{version}"
            )

    async def list_all_subjects(self) -> list[SubjectName]:
        try:
            subjects: list[str] = await self.client.get_subjects()
            logger.info(f"Retrieved {len(subjects)} subjects from Schema Registry")
            return subjects
        except SchemaRegistryError as exc:
            self._raise_schema_registry_runtime_error("List all subjects", exc)

    @handle_schema_registry_error("Get schema versions")
    async def get_schema_versions(self, subject: SubjectName) -> list[int]:
        versions = await self.client.get_versions(subject)
        return sorted(versions)

    @handle_schema_registry_error(
        "Get schema by version",
        lambda self, subject, version: f"{subject} v{version}",
    )
    async def get_schema_by_version(self, subject: SubjectName, version: int) -> SchemaVersionInfo:
        schema_version = await self.client.get_version(subject, version)

        if schema_version and schema_version.schema:
            schema_str = schema_version.schema.schema_str or ""
            return SchemaVersionInfo(
                version=schema_version.version,
                schema_id=schema_version.schema_id,
                schema=schema_str,
                schema_type=schema_version.schema.schema_type,
                references=[
                    Reference(name=ref.name, subject=ref.subject, version=ref.version)
                    for ref in (getattr(schema_version, "references", None) or [])
                ],
                hash=self._calculate_schema_hash(schema_str),
                canonical_hash=self._canonicalize_and_hash(schema_str),
            )

        raise RuntimeError(f"Schema not found for {subject} version {version}")

    async def set_compatibility_mode(self, subject: SubjectName, mode: str) -> None:
        try:
            compatibility_level = ConfigCompatibilityLevel(mode)
            config = ServerConfig(compatibility=cast(Any, compatibility_level))
            await self.client.set_config(subject_name=subject, config=config)
            logger.info(f"Compatibility mode set: {subject} -> {mode}")
        except SchemaRegistryError as exc:
            self._raise_schema_registry_runtime_error("Set compatibility mode", exc, subject)

    def _extract_schema_string(self, spec: DomainSchemaSpec) -> str:
        if spec.schema:
            return spec.schema

        if spec.source:
            if spec.source.inline:
                return spec.source.inline
            if spec.source.yaml:
                return spec.source.yaml
            if spec.source.file:
                raise ValueError(
                    f"File-based schema source for {spec.subject} must be converted to inline before registration. "
                    f"File path: {spec.source.file}"
                )

        raise ValueError(f"No schema content found for subject {spec.subject}")

    def _calculate_schema_hash(self, schema_str: str) -> str:
        return hashlib.sha256(schema_str.encode()).hexdigest()

    def _canonicalize_and_hash(self, schema_str: str) -> str:
        try:
            schema_dict = orjson.loads(schema_str)
            canonical = orjson.dumps(schema_dict, option=orjson.OPT_SORT_KEYS)
            return hashlib.sha256(canonical).hexdigest()
        except Exception:
            return hashlib.sha256(schema_str.encode()).hexdigest()

    def _normalize_schema_string(self, schema_str: str) -> str:
        import json

        if schema_str.startswith("\ufeff"):
            schema_str = schema_str[1:]

        schema_str = schema_str.replace("\r\n", "\n").replace("\r", "\n")
        schema_str = schema_str.strip()

        try:
            parsed = json.loads(schema_str)
            schema_str = json.dumps(parsed, ensure_ascii=True, separators=(",", ":"))
        except Exception:
            schema_str = schema_str.encode("ascii", "backslashreplace").decode("ascii")

        return schema_str

    async def _get_latest_schema_version_info(self, subject: SubjectName) -> SchemaVersionInfo:
        versions = await self.client.get_versions(subject)
        if not versions:
            raise RuntimeError(f"Schema not found for {subject}")

        latest_version = max(versions)
        schema_version = await self.client.get_version(subject, latest_version)
        if not schema_version or not schema_version.schema:
            raise RuntimeError(f"Schema not found for {subject} version {latest_version}")

        schema_str = schema_version.schema.schema_str or ""
        return SchemaVersionInfo(
            version=schema_version.version,
            schema_id=schema_version.schema_id,
            schema=schema_str,
            schema_type=schema_version.schema.schema_type,
            references=[
                Reference(name=ref.name, subject=ref.subject, version=ref.version)
                for ref in (getattr(schema_version, "references", None) or [])
            ],
            hash=self._calculate_schema_hash(schema_str),
            canonical_hash=self._canonicalize_and_hash(schema_str),
        )

    def _raise_schema_registry_runtime_error(
        self,
        operation: str,
        exc: SchemaRegistryError,
        context: str | None = None,
    ) -> NoReturn:
        context_msg = f" ({context})" if context else ""
        error_msg = f"{operation} failed{context_msg}: {exc}"
        logger.error(error_msg)
        raise RuntimeError(error_msg) from exc
