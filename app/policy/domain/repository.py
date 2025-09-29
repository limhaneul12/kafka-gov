"""Policy 저장소 인터페이스"""

from __future__ import annotations

from abc import ABC, abstractmethod

from .models import DomainEnvironment, DomainPolicySet, DomainResourceType


class IPolicyRepository(ABC):
    """정책 저장소 인터페이스"""

    @abstractmethod
    async def get_policy_set(
        self, environment: DomainEnvironment, resource_type: DomainResourceType
    ) -> DomainPolicySet | None:
        """정책 집합 조회"""

    @abstractmethod
    async def save_policy_set(self, policy_set: DomainPolicySet) -> None:
        """정책 집합 저장"""

    @abstractmethod
    async def delete_policy_set(
        self, environment: DomainEnvironment, resource_type: DomainResourceType
    ) -> bool:
        """정책 집합 삭제

        Returns:
            삭제 성공 여부
        """

    @abstractmethod
    async def list_environments(self) -> list[DomainEnvironment]:
        """등록된 환경 목록"""

    @abstractmethod
    async def list_resource_types(self, environment: DomainEnvironment) -> list[DomainResourceType]:
        """환경별 리소스 타입 목록"""
