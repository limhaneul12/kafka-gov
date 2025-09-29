"""Schema Domain Repository 인터페이스"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import Any

from ..models import (
    ChangeId,
    DomainSchemaApplyResult,
    DomainSchemaArtifact,
    DomainSchemaCompatibilityReport,
    DomainSchemaPlan,
    DomainSchemaSpec,
    DomainSchemaUploadResult,
    SubjectName,
)


class ISchemaRegistryRepository(ABC):
    """Schema Registry 어댑터 인터페이스"""

    @abstractmethod
    async def describe_subjects(
        self, subjects: Iterable[SubjectName]
    ) -> dict[SubjectName, dict[str, Any]]:
        """Subject들의 최신 버전 및 메타데이터 조회"""

    @abstractmethod
    async def check_compatibility(
        self,
        spec: DomainSchemaSpec,
        references: list[dict[str, Any]] | None = None,
    ) -> DomainSchemaCompatibilityReport:
        """호환성 검증"""

    @abstractmethod
    async def register_schema(
        self,
        spec: DomainSchemaSpec,
        compatibility: bool = True,
    ) -> int:
        """스키마 등록 후 버전 반환"""

    @abstractmethod
    async def delete_subject(self, subject: SubjectName) -> None:
        """Subject 삭제"""


class ISchemaMetadataRepository(ABC):
    """스키마 메타데이터/Audit Repository 인터페이스"""

    @abstractmethod
    async def save_plan(self, plan: DomainSchemaPlan, created_by: str) -> None:
        pass

    @abstractmethod
    async def get_plan(self, change_id: ChangeId) -> DomainSchemaPlan | None:
        pass

    @abstractmethod
    async def save_apply_result(self, result: DomainSchemaApplyResult, applied_by: str) -> None:
        pass

    @abstractmethod
    async def record_artifact(self, artifact: DomainSchemaArtifact, change_id: ChangeId) -> None:
        pass

    @abstractmethod
    async def save_upload_result(self, upload: DomainSchemaUploadResult, uploaded_by: str) -> None:
        pass


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
        pass


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
        pass
