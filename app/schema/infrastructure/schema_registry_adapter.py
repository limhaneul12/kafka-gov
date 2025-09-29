"""Schema Registry 비동기 어댑터 - Confluent Kafka Python 비동기 기반"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from typing import Any

from confluent_kafka.schema_registry import AsyncSchemaRegistryClient, Schema
from confluent_kafka.schema_registry.error import SchemaRegistryError

from ..domain.models import (
    DomainSchemaCompatibilityIssue,
    DomainSchemaCompatibilityReport,
    DomainSchemaSpec,
    SubjectName,
)
from ..domain.repositories.interfaces import ISchemaRegistryRepository

logger = logging.getLogger(__name__)


class ConfluentSchemaRegistryAdapter(ISchemaRegistryRepository):
    """Confluent Schema Registry 비동기 어댑터"""

    def __init__(self, client: AsyncSchemaRegistryClient) -> None:
        self.client = client

    async def describe_subjects(
        self, subjects: Iterable[SubjectName]
    ) -> dict[SubjectName, dict[str, Any]]:
        subject_list = list(subjects)
        result: dict[SubjectName, dict[str, Any]] = {}

        try:
            # 모든 subject 목록 조회 (1번의 API 호출)
            all_subjects = await self.client.get_subjects()

            for subject in subject_list:
                if subject not in all_subjects:
                    continue

                try:
                    # 최신 버전 조회
                    latest_version = await self.client.get_latest_version(subject)

                    if latest_version and latest_version.schema:
                        result[subject] = {
                            "version": latest_version.version,
                            "schema_id": latest_version.schema_id,
                            "schema": latest_version.schema.schema_str,
                            "schema_type": latest_version.schema.schema_type,
                            "references": [
                                {
                                    "name": ref.name,
                                    "subject": ref.subject,
                                    "version": ref.version,
                                }
                                for ref in (getattr(latest_version, "references", None) or [])
                            ],
                            "hash": self._calculate_schema_hash(
                                latest_version.schema.schema_str or ""
                            ),
                        }
                except SchemaRegistryError as e:
                    logger.warning(f"Failed to get schema for subject {subject}: {e}")
                    continue
            return result

        except SchemaRegistryError as e:
            logger.error(f"Failed to describe subjects: {e}")
            raise RuntimeError(f"Schema Registry error: {e}") from e

    async def check_compatibility(
        self,
        spec: DomainSchemaSpec,
        references: list[dict[str, Any]] | None = None,
    ) -> DomainSchemaCompatibilityReport:
        """호환성 검증"""
        try:
            # 스키마 정의 추출
            schema_str = self._extract_schema_string(spec)

            # Schema 객체 생성
            schema_obj = Schema(
                schema_str=schema_str,
                schema_type=spec.schema_type.value,
                references=references or [],
            )

            # 호환성 검증 실행
            is_compatible = await self.client.test_compatibility(
                subject_name=spec.subject,
                schema=schema_obj,
            )

            return DomainSchemaCompatibilityReport(
                subject=spec.subject,
                mode=spec.compatibility,
                is_compatible=is_compatible,
                issues=(),  # Confluent 클라이언트는 상세 이슈를 제공하지 않음
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

    async def check_compatibility_batch(
        self, specs: list[DomainSchemaSpec]
    ) -> dict[SubjectName, DomainSchemaCompatibilityReport]:
        """배치 호환성 검증 (성능 최적화)"""
        results: dict[SubjectName, DomainSchemaCompatibilityReport] = {}

        for spec in specs:
            report = await self.check_compatibility(spec)
            results[spec.subject] = report

        return results

    async def register_schema(
        self,
        spec: DomainSchemaSpec,
        compatibility: bool = True,
    ) -> int:
        """스키마 등록 후 버전 반환"""
        try:
            schema_str = self._extract_schema_string(spec)

            # 참조 변환
            references = [
                {
                    "name": ref.name,
                    "subject": ref.subject,
                    "version": ref.version,
                }
                for ref in spec.references
            ]

            # Schema 객체 생성
            schema_obj = Schema(
                schema_str=schema_str,
                schema_type=spec.schema_type.value,
                references=references if references else [],
            )

            # 스키마 등록
            schema_id = await self.client.register_schema(
                subject_name=spec.subject,
                schema=schema_obj,
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
            deleted_versions = await self.client.delete_subject(subject)
            logger.info(f"Subject deleted: {subject} ({len(deleted_versions)} versions)")

        except SchemaRegistryError as e:
            logger.error(f"Failed to delete subject {subject}: {e}")
            raise RuntimeError(f"Subject deletion failed: {e}") from e

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
                # 파일에서 읽기 (실제 구현에서는 파일 시스템 또는 오브젝트 스토리지에서 읽음)
                raise NotImplementedError("File-based schema source not implemented yet")

        raise ValueError(f"No schema content found for subject {spec.subject}")

    def _calculate_schema_hash(self, schema_str: str) -> str:
        """스키마 해시 계산"""
        import hashlib

        return hashlib.sha256(schema_str.encode()).hexdigest()[:16]


# 의존성 주입용 팩토리 함수
def create_async_schema_registry_client(url: str, **config: Any) -> AsyncSchemaRegistryClient:
    """비동기 Schema Registry 클라이언트 생성"""
    client_config = {
        "url": url,
        **config,
    }
    return AsyncSchemaRegistryClient(client_config)


def create_schema_registry_adapter(
    client: AsyncSchemaRegistryClient,
) -> ConfluentSchemaRegistryAdapter:
    """Schema Registry 어댑터 생성"""
    return ConfluentSchemaRegistryAdapter(client)
