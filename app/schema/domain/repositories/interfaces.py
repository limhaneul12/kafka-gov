"""Schema Domain Repository 인터페이스"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import Any

from ..models import (
    ChangeId,
    DescribeResult,
    DomainSchemaApplyResult,
    DomainSchemaArtifact,
    DomainSchemaCompatibilityReport,
    DomainSchemaPlan,
    DomainSchemaSpec,
    DomainSchemaUploadResult,
    Reference,
    SubjectName,
)


class ISchemaRegistryRepository(ABC):
    """Schema Registry 어댑터 인터페이스"""

    @abstractmethod
    async def describe_subjects(self, subjects: Iterable[SubjectName]) -> DescribeResult:
        """Subject들의 최신 버전 및 메타데이터 조회"""

    @abstractmethod
    async def check_compatibility(
        self, spec: DomainSchemaSpec, references: list[Reference] | None = None
    ) -> DomainSchemaCompatibilityReport:
        """호환성 검증"""

    @abstractmethod
    async def register_schema(self, spec: DomainSchemaSpec, compatibility: bool = True) -> int:
        """스키마 등록 후 버전 반환"""

    @abstractmethod
    async def delete_subject(self, subject: SubjectName) -> None:
        """Subject 삭제"""

    @abstractmethod
    async def list_all_subjects(self) -> list[SubjectName]:
        """Schema Registry의 모든 Subject 목록 조회"""


class ISchemaMetadataRepository(ABC):
    """스키마 메타데이터/Audit Repository 인터페이스"""

    @abstractmethod
    async def save_plan(self, plan: DomainSchemaPlan, created_by: str) -> None:
        """계획 저장"""

    @abstractmethod
    async def get_plan(self, change_id: ChangeId) -> DomainSchemaPlan | None:
        """계획 조회"""

    @abstractmethod
    async def save_apply_result(self, result: DomainSchemaApplyResult, applied_by: str) -> None:
        """적용 결과 저장"""

    @abstractmethod
    async def record_artifact(self, artifact: DomainSchemaArtifact, change_id: ChangeId) -> None:
        """아티팩트 기록"""

    @abstractmethod
    async def save_upload_result(self, upload: DomainSchemaUploadResult, uploaded_by: str) -> None:
        """업로드 결과 저장"""

    @abstractmethod
    async def list_artifacts(self) -> list[DomainSchemaArtifact]:
        """모든 스키마 아티팩트 목록 조회"""

    @abstractmethod
    async def delete_artifact_by_subject(self, subject: SubjectName) -> None:
        """Subject별 아티팩트 삭제"""


class ISchemaAuditRepository(ABC):
    """감사 로그 리포지토리"""

    @abstractmethod
    async def log_operation(
        self,
        change_id: ChangeId,
        action: str,
        target: SubjectName,
        actor: str,
        status: str,
        message: str | None = None,
        snapshot: dict[str, Any] | None = None,
    ) -> str:
        """감사 로그 기록"""


class IObjectStorageRepository(ABC):
    """스키마 아티팩트 저장소 인터페이스"""

    @abstractmethod
    async def put_object(
        self,
        key: str,
        data: bytes,
        metadata: dict[str, str] | None = None,
    ) -> str:
        """객체 저장 후 접근 URL 반환"""

    @abstractmethod
    async def delete_prefix(self, prefix: str) -> None:
        """prefix로 객체 삭제"""
