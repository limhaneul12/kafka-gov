"""메모리 기반 정책 저장소 (개발/테스트용)"""

from __future__ import annotations

from ..domain import Environment, IPolicyRepository, PolicySet, ResourceType


class MemoryPolicyRepository(IPolicyRepository):
    """메모리 기반 정책 저장소"""
    
    def __init__(self) -> None:
        self._policy_sets: dict[tuple[Environment, ResourceType], PolicySet] = {}
    
    async def get_policy_set(
        self, 
        environment: Environment, 
        resource_type: ResourceType
    ) -> PolicySet | None:
        """정책 집합 조회"""
        key = (environment, resource_type)
        return self._policy_sets.get(key)
    
    async def save_policy_set(self, policy_set: PolicySet) -> None:
        """정책 집합 저장"""
        key = (policy_set.environment, policy_set.resource_type)
        self._policy_sets[key] = policy_set
    
    async def delete_policy_set(
        self, 
        environment: Environment, 
        resource_type: ResourceType
    ) -> bool:
        """정책 집합 삭제"""
        key = (environment, resource_type)
        if key in self._policy_sets:
            del self._policy_sets[key]
            return True
        return False
    
    async def list_environments(self) -> list[Environment]:
        """등록된 환경 목록"""
        return list({env for env, _ in self._policy_sets})
    
    async def list_resource_types(self, environment: Environment) -> list[ResourceType]:
        """환경별 리소스 타입 목록"""
        return [rt for env, rt in self._policy_sets if env == environment]
