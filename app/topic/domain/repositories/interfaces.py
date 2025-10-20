"""Topic Domain Repository 인터페이스"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, TypedDict

from ..models import ChangeId, DomainTopicApplyResult, DomainTopicPlan, DomainTopicSpec, TopicName

if TYPE_CHECKING:
    from ..policies.management.models import PolicyStatus, PolicyType, StoredPolicy


class ITopicRepository(ABC):
    """토픽 리포지토리 인터페이스"""

    @abstractmethod
    async def list_topics(self) -> list[TopicName]:
        """모든 토픽 목록 조회"""
        ...

    @abstractmethod
    async def get_topic_metadata(self, name: TopicName) -> dict[str, Any] | None:
        """토픽 메타데이터 조회"""
        ...

    @abstractmethod
    async def create_topics(
        self, specs: list[DomainTopicSpec]
    ) -> dict[TopicName, Exception | None]:
        """토픽 생성"""
        ...

    @abstractmethod
    async def delete_topics(self, names: list[TopicName]) -> dict[TopicName, Exception | None]:
        """토픽 삭제"""
        ...

    @abstractmethod
    async def alter_topic_configs(
        self, configs: dict[TopicName, dict[str, str]]
    ) -> dict[TopicName, Exception | None]:
        """토픽 설정 변경"""
        ...

    @abstractmethod
    async def create_partitions(
        self, partitions: dict[TopicName, int]
    ) -> dict[TopicName, Exception | None]:
        """파티션 수 증가"""
        ...

    @abstractmethod
    async def describe_topics(self, names: list[TopicName]) -> dict[TopicName, dict[str, Any]]:
        """토픽 상세 정보 조회"""
        ...


class PlanMeta(TypedDict):
    """토픽 계획 메타 정보 타입

    - status: 계획 상태 (pending/applied/failed)
    - created_at: 계획 생성 시각 (ISO8601 문자열)
    - applied_at: 계획 적용 시각 (ISO8601 문자열) 또는 없음
    """

    status: str
    created_at: str
    applied_at: str | None


class ITopicMetadataRepository(ABC):
    """토픽 메타데이터 리포지토리 인터페이스"""

    @abstractmethod
    async def save_plan(self, plan: DomainTopicPlan, created_by: str) -> None:
        """계획 저장"""
        ...

    @abstractmethod
    async def get_plan(self, change_id: ChangeId) -> DomainTopicPlan | None:
        """계획 조회"""
        ...

    @abstractmethod
    async def get_plan_meta(self, change_id: ChangeId) -> PlanMeta | None:
        """계획 메타 정보 조회 (상태/타임스탬프)

        Returns:
            PlanMeta dict 또는 None
        """
        ...

    @abstractmethod
    async def save_apply_result(self, result: DomainTopicApplyResult, applied_by: str) -> None:
        """적용 결과 저장"""
        ...

    @abstractmethod
    async def get_topic_metadata(self, name: TopicName) -> dict[str, Any] | None:
        """토픽 메타데이터 조회"""
        ...

    @abstractmethod
    async def save_topic_metadata(self, name: TopicName, metadata: dict[str, Any]) -> None:
        """토픽 메타데이터 저장"""
        ...

    @abstractmethod
    async def delete_topic_metadata(self, name: TopicName) -> None:
        """토픽 메타데이터 삭제"""
        ...


class IAuditRepository(ABC):
    """감사 로그 리포지토리 인터페이스"""

    @abstractmethod
    async def log_topic_operation(
        self,
        change_id: ChangeId,
        action: str,
        target: TopicName,
        actor: str,
        status: str,
        message: str | None = None,
        snapshot: dict[str, Any] | None = None,
        team: str | None = None,
    ) -> str:
        """토픽 작업 감사 로그 기록"""
        ...


class IPolicyRepository(ABC):
    """Policy repository interface for custom policies"""

    @abstractmethod
    async def create_policy(
        self,
        policy_type: PolicyType,
        name: str,
        description: str,
        content: dict,
        created_by: str,
        target_environment: str = "total",
    ) -> StoredPolicy:
        """Create new custom policy

        Args:
            policy_type: Type of policy (naming or guardrail)
            name: Policy name
            description: Policy description
            content: Policy configuration (dict)
            created_by: User who created the policy
            target_environment: Target environment (dev/stg/prod/total)

        Returns:
            Created policy with version=1, status=DRAFT
        """
        ...

    @abstractmethod
    async def get_policy(self, policy_id: str, version: int | None = None) -> StoredPolicy | None:
        """Get policy by ID

        Args:
            policy_id: Policy UUID
            version: Version number (None = latest version)

        Returns:
            Policy if found, None otherwise
        """
        ...

    @abstractmethod
    async def get_active_policy(self, policy_id: str) -> StoredPolicy | None:
        """Get active policy by ID

        Args:
            policy_id: Policy UUID

        Returns:
            Policy if found and active, None otherwise
        """
        ...

    @abstractmethod
    async def list_policies(
        self,
        policy_type: PolicyType | None = None,
        status: PolicyStatus | None = None,
    ) -> list[StoredPolicy]:
        """List policies with optional filters

        Args:
            policy_type: Filter by type (None = all types)
            status: Filter by status (None = all statuses)

        Returns:
            List of policies matching filters (latest versions only)
        """
        ...

    @abstractmethod
    async def list_policy_versions(self, policy_id: str) -> list[StoredPolicy]:
        """List all versions of a policy

        Args:
            policy_id: Policy UUID

        Returns:
            List of all policy versions (newest first)
        """
        ...

    @abstractmethod
    async def update_policy(
        self,
        policy_id: str,
        name: str | None = None,
        description: str | None = None,
        content: dict | None = None,
        target_environment: str | None = None,
    ) -> StoredPolicy:
        """Update policy (creates new version)

        Args:
            policy_id: Policy UUID
            name: New name (None = keep current)
            description: New description (None = keep current)
            content: New content (None = keep current)
            target_environment: Target environment (None = keep current)

        Returns:
            Updated policy with incremented version

        Raises:
            ValueError: If policy not found or not in DRAFT status
        """
        ...

    @abstractmethod
    async def activate_policy(self, policy_id: str, version: int | None = None) -> StoredPolicy:
        """Activate policy (DRAFT → ACTIVE)

        Args:
            policy_id: Policy UUID
            version: Version to activate (None = latest DRAFT)

        Returns:
            Activated policy

        Raises:
            ValueError: If policy not found or no DRAFT version
        """
        ...

    @abstractmethod
    async def archive_policy(self, policy_id: str) -> StoredPolicy:
        """Archive policy (ACTIVE → ARCHIVED)

        Args:
            policy_id: Policy UUID

        Returns:
            Archived policy

        Raises:
            ValueError: If policy not found
        """
        ...

    @abstractmethod
    async def delete_policy(self, policy_id: str, version: int | None = None) -> None:
        """Delete policy (non-ACTIVE versions only)

        Args:
            policy_id: Policy UUID
            version: Version to delete (None = delete all DRAFT versions)

        Raises:
            ValueError: If policy not found or is ACTIVE
        """
        ...

    @abstractmethod
    async def delete_all_policy_versions(self, policy_id: str) -> None:
        """Delete all versions of a policy (including ACTIVE/ARCHIVED)

        Args:
            policy_id: Policy UUID

        Raises:
            ValueError: If policy not found
        """
        ...

    @abstractmethod
    async def rollback_to_version(
        self, policy_id: str, target_version: int, created_by: str = "system"
    ) -> StoredPolicy:
        """Rollback policy to previous version (activates target version)

        Args:
            policy_id: Policy UUID
            target_version: Version to rollback to
            created_by: User who triggered rollback (not used)

        Returns:
            Target version with ACTIVE status

        Raises:
            ValueError: If target version not found
        """
        ...
