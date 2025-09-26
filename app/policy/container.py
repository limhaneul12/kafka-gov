"""Policy 모듈 DI 컨테이너"""

from __future__ import annotations

from pathlib import Path

from dependency_injector import containers, providers

from .application import (
    DefaultPolicyFactory,
    PolicyEvaluationService,
    PolicyManagementService,
)
from .domain import PolicyEngine
from .infrastructure import FilePolicyRepository, MemoryPolicyRepository


class PolicyContainer(containers.DeclarativeContainer):
    """Policy 모듈 의존성 컨테이너"""
    
    # Configuration
    config = providers.Configuration()
    
    # Policy Engine (싱글톤)
    policy_engine = providers.Singleton(PolicyEngine)
    
    # Repository (환경에 따라 선택)
    policy_repository = providers.Factory(
        MemoryPolicyRepository,
    )
    
    # File Repository (설정 파일 기반)
    file_policy_repository = providers.Factory(
        FilePolicyRepository,
        config_dir=providers.Factory(
            Path,
            config.policy.config_dir.as_(str, default="/tmp/policy_configs")
        ),
    )
    
    # Services
    policy_evaluation_service = providers.Factory(
        PolicyEvaluationService,
        policy_engine=policy_engine,
        policy_repository=policy_repository,
    )
    
    policy_management_service = providers.Factory(
        PolicyManagementService,
        policy_engine=policy_engine,
        policy_repository=policy_repository,
    )
    
    # Factory
    default_policy_factory = providers.Factory(DefaultPolicyFactory)


class PolicyUseCaseFactory:
    """Policy 유스케이스 팩토리"""
    
    def __init__(self, container: PolicyContainer) -> None:
        self._container = container
    
    def get_policy_evaluation_service(self) -> PolicyEvaluationService:
        """정책 평가 서비스 조회"""
        return self._container.policy_evaluation_service()
    
    def get_policy_management_service(self) -> PolicyManagementService:
        """정책 관리 서비스 조회"""
        return self._container.policy_management_service()
    
    def get_policy_engine(self) -> PolicyEngine:
        """정책 엔진 조회"""
        return self._container.policy_engine()
    
    async def initialize_default_policies(self) -> None:
        """기본 정책 초기화"""
        factory = self._container.default_policy_factory()
        management_service = self.get_policy_management_service()
        
        # Topic 기본 정책 등록
        topic_policies = factory.create_topic_policies()
        for env, policy_set in topic_policies.items():
            await management_service.update_policy_set(
                environment=env,
                resource_type=policy_set.resource_type,
                policy_set=policy_set,
            )
        
        # Schema 기본 정책 등록
        schema_policies = factory.create_schema_policies()
        for env, policy_set in schema_policies.items():
            await management_service.update_policy_set(
                environment=env,
                resource_type=policy_set.resource_type,
                policy_set=policy_set,
            )


# 전역 컨테이너 인스턴스
policy_container = PolicyContainer()
policy_use_case_factory = PolicyUseCaseFactory(policy_container)
