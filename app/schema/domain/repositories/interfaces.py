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
    SchemaVersionInfo,
    SubjectName,
)
from ..models.policy_management import DomainSchemaPolicy, SchemaPolicyStatus, SchemaPolicyType


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
    async def register_schema(
        self, spec: DomainSchemaSpec, compatibility: bool = True
    ) -> tuple[int, int]:
        """스키마 등록 후 (버전, 스키마 ID) 반환"""

    @abstractmethod
    async def delete_subject(self, subject: SubjectName) -> None:
        """Subject 삭제"""

    @abstractmethod
    async def delete_version(self, subject: SubjectName, version: int) -> None:
        """Subject의 특정 버전 삭제"""

    @abstractmethod
    async def list_all_subjects(self) -> list[SubjectName]:
        """Schema Registry의 모든 Subject 목록 조회"""

    @abstractmethod
    async def set_compatibility_mode(self, subject: SubjectName, mode: str) -> None:
        """Subject의 호환성 모드 설정"""

    @abstractmethod
    async def get_schema_versions(self, subject: SubjectName) -> list[int]:
        """Subject의 전체 버전 목록 조회"""

    @abstractmethod
    async def get_schema_by_version(self, subject: SubjectName, version: int) -> SchemaVersionInfo:
        """Subject의 특정 버전 상세 조회"""


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

    @abstractmethod
    async def delete_artifacts_newer_than(self, subject: SubjectName, version: int) -> None:
        """Subject의 특정 버전보다 새로운 아티팩트 삭제"""

    @abstractmethod
    async def save_schema_metadata(self, subject: SubjectName, metadata: dict[str, Any]) -> None:
        """스키마 메타데이터 저장"""

    @abstractmethod
    async def search_artifacts(
        self,
        query: str | None = None,
        owner: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[DomainSchemaArtifact], int]:
        """아티팩트 검색 (필터링 및 페이지네이션)

        Returns:
            (artifacts, total_count)
        """

    @abstractmethod
    async def get_latest_artifact(self, subject: SubjectName) -> DomainSchemaArtifact | None:
        """Subject의 최신 아티팩트 조회"""

    @abstractmethod
    async def get_schema_metadata(self, subject: SubjectName) -> dict[str, Any] | None:
        """Subject의 메타데이터 조회"""


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


class ISchemaPolicyRepository(ABC):
    """스키마 정책 리포지토리 인터페이스"""

    @abstractmethod
    async def save(self, policy: DomainSchemaPolicy) -> None:
        """정책 저장 (버전 관리 포함)"""

    @abstractmethod
    async def get_by_id(
        self, policy_id: str, version: int | None = None
    ) -> DomainSchemaPolicy | None:
        """특정 ID와 버전의 정책 조회 (버전 생략 시 최신 버전)"""

    @abstractmethod
    async def list_active_policies(
        self, env: str | None = None, policy_type: SchemaPolicyType | None = None
    ) -> list[DomainSchemaPolicy]:
        """활성화된 정책 목록 조회"""

    @abstractmethod
    async def list_all_policies(
        self, env: str | None = None, policy_type: SchemaPolicyType | None = None
    ) -> list[DomainSchemaPolicy]:
        """모든 정책 목록 조회 (상태 무관)"""

    @abstractmethod
    async def get_history(self, policy_id: str) -> list[DomainSchemaPolicy]:
        """정책의 모든 버전 이력 조회"""

    @abstractmethod
    async def update_status(self, policy_id: str, version: int, status: SchemaPolicyStatus) -> None:
        """정책 상태 업데이트"""

    @abstractmethod
    async def delete_policy(self, policy_id: str) -> None:
        """정책의 모든 버전 삭제"""

    @abstractmethod
    async def delete_version(self, policy_id: str, version: int) -> None:
        """정책의 특정 버전 삭제"""
