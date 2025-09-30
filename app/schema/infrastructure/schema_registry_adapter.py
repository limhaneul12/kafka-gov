"""Schema Registry 비동기 어댑터 - Confluent Kafka Python 비동기 기반"""

from __future__ import annotations

import asyncio
import hashlib
import logging
from collections.abc import Iterable

from confluent_kafka.schema_registry import AsyncSchemaRegistryClient, Schema
from confluent_kafka.schema_registry.error import SchemaRegistryError

from ..domain.models import (
    CompatibilityResult,
    DescribeResult,
    DomainSchemaCompatibilityIssue,
    DomainSchemaCompatibilityReport,
    DomainSchemaSpec,
    Reference,
    SchemaVersionInfo,
    SubjectName,
)
from ..domain.repositories.interfaces import ISchemaRegistryRepository

logger = logging.getLogger(__name__)


class ConfluentSchemaRegistryAdapter(ISchemaRegistryRepository):
    """Confluent Schema Registry 비동기 어댑터"""

    def __init__(self, client: AsyncSchemaRegistryClient) -> None:
        self.client = client

    async def describe_subjects(self, subjects: Iterable[SubjectName]) -> DescribeResult:
        subject_list: list[SubjectName] = list(subjects)
        result: DescribeResult = {}

        try:
            # 모든 subject 목록 조회 (1번의 API 호출)
            all_subjects: list[str] = await self.client.get_subjects()

            for subject in subject_list:
                if subject not in all_subjects:
                    continue

                try:
                    # 최신 버전 조회
                    latest_version = await self.client.get_latest_version(subject)

                    if latest_version and latest_version.schema:
                        result[subject] = SchemaVersionInfo(
                            version=latest_version.version,
                            schema_id=latest_version.schema_id,
                            schema=latest_version.schema.schema_str,
                            schema_type=latest_version.schema.schema_type,
                            references=[
                                Reference(
                                    name=ref.name,
                                    subject=ref.subject,
                                    version=ref.version,
                                )
                                for ref in (getattr(latest_version, "references", None) or [])
                            ],
                            hash=self._calculate_schema_hash(
                                latest_version.schema.schema_str or ""
                            ),
                        )
                except SchemaRegistryError as e:
                    logger.warning(f"Failed to get schema for subject {subject}: {e}")
                    continue

            return result

        except SchemaRegistryError as e:
            logger.error(f"Failed to describe subjects: {e}")
            raise RuntimeError(f"Schema Registry error: {e}") from e

    async def check_compatibility(
        self, spec: DomainSchemaSpec, references: list[Reference] | None = None
    ) -> DomainSchemaCompatibilityReport:
        """호환성 검증"""
        try:
            # 스키마 정의 추출
            schema_str: str = self._extract_schema_string(spec)

            # Schema 객체 생성
            schema_obj = Schema(
                schema_str=schema_str,
                schema_type=spec.schema_type.value,
                references=[ref.to_dict() for ref in references] if references else [],
            )

            # 호환성 검증 실행
            is_compatible: bool = await self.client.test_compatibility(
                subject_name=spec.subject, schema=schema_obj
            )

            # Confluent 클라이언트는 상세 이슈를 제공하지 않음 issues는 빈 튜플로 반환
            return DomainSchemaCompatibilityReport(
                subject=spec.subject,
                mode=spec.compatibility,
                is_compatible=is_compatible,
                issues=(),
            )

        except SchemaRegistryError as e:
            logger.warning(f"Compatibility check failed for {spec.subject}: {e}")

            # 에러를 호환성 이슈로 변환
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
        """배치 호환성 검증 (병렬 처리로 성능 최적화)"""
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
        results = await asyncio.gather(*tasks, return_exceptions=True)

        compatibility_result: CompatibilityResult = {}
        for spec, result in zip(specs, results, strict=True):
            if isinstance(result, Exception):
                logger.error(f"Compatibility check failed for {spec.subject}: {result}")
                # 에러를 호환성 이슈로 변환
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

    async def register_schema(self, spec: DomainSchemaSpec, compatibility: bool = True) -> int:
        """스키마 등록 후 버전 반환"""
        try:
            schema_str: str = self._extract_schema_string(spec)

            # 참조 변환
            references_list: list[dict[str, int | str]] = [
                Reference(
                    name=ref.name,
                    subject=ref.subject,
                    version=ref.version,
                ).to_dict()
                for ref in spec.references
            ]

            # 스키마 등록
            schema_id = await self.client.register_schema(
                subject_name=spec.subject,
                schema=Schema(
                    schema_str=schema_str,
                    schema_type=spec.schema_type.value,
                    references=references_list,
                ),
            )

            # 등록된 버전 조회
            latest_version = await self.client.get_latest_version(spec.subject)

            if latest_version and latest_version.version is not None:
                logger.info(
                    f"Schema registered: {spec.subject} v{latest_version.version} (ID: {schema_id})"
                )
                return latest_version.version
            else:
                logger.warning(f"Could not retrieve version for registered schema {spec.subject}")
                return 1  # 기본값으로 1 반환

        except SchemaRegistryError as e:
            logger.error(f"Failed to register schema {spec.subject}: {e}")
            raise RuntimeError(f"Schema registration failed: {e}") from e

    async def delete_subject(self, subject: SubjectName) -> None:
        """Subject 삭제"""
        try:
            # 모든 버전 삭제
            deleted_versions: list[int] = await self.client.delete_subject(subject)
            logger.info(f"Subject deleted: {subject} ({len(deleted_versions)} versions)")

        except SchemaRegistryError as e:
            logger.error(f"Failed to delete subject {subject}: {e}")
            raise RuntimeError(f"Subject deletion failed: {e}") from e

    async def get_schema_versions(self, subject: SubjectName) -> list[int]:
        """Subject의 모든 버전 목록 조회"""
        try:
            versions = await self.client.get_versions(subject)
            return sorted(versions)
        except SchemaRegistryError as e:
            logger.error(f"Failed to get versions for subject {subject}: {e}")
            raise RuntimeError(f"Version retrieval failed: {e}") from e

    async def get_schema_by_version(self, subject: SubjectName, version: int) -> SchemaVersionInfo:
        """특정 버전의 스키마 조회"""
        try:
            schema_version = await self.client.get_version(subject, version)

            if schema_version and schema_version.schema:
                return SchemaVersionInfo(
                    version=schema_version.version,
                    schema_id=schema_version.schema_id,
                    schema=schema_version.schema.schema_str,
                    schema_type=schema_version.schema.schema_type,
                    references=[
                        Reference(name=ref.name, subject=ref.subject, version=ref.version)
                        for ref in (getattr(schema_version, "references", None) or [])
                    ],
                    hash=self._calculate_schema_hash(schema_version.schema.schema_str or ""),
                )

            else:
                raise RuntimeError(f"Schema not found for {subject} version {version}")

        except SchemaRegistryError as e:
            logger.error(f"Failed to get schema {subject} version {version}: {e}")
            raise RuntimeError(f"Schema retrieval failed: {e}") from e

    def _extract_schema_string(self, spec: DomainSchemaSpec) -> str:
        """스키마 명세에서 스키마 문자열 추출"""
        if spec.schema:
            return spec.schema

        if spec.source:
            if spec.source.inline:
                return spec.source.inline
            elif spec.source.yaml:
                return spec.source.yaml
            elif spec.source.file:
                # 파일 경로가 제공된 경우 - 실제로는 업로드 시 inline으로 변환되어야 함
                # 여기서는 에러 대신 명확한 메시지 반환
                raise ValueError(
                    f"File-based schema source for {spec.subject} must be converted to inline before registration. "
                    f"File path: {spec.source.file}"
                )

        raise ValueError(f"No schema content found for subject {spec.subject}")

    def _calculate_schema_hash(self, schema_str: str) -> str:
        """스키마 해시 계산"""
        return hashlib.sha256(schema_str.encode()).hexdigest()[:16]
