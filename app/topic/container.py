"""Topic 모듈 DI 컨테이너"""

from __future__ import annotations

from typing import Annotated

from dependency_injector import containers, providers
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ...policy import policy_use_case_factory
from ...shared.container import infrastructure_container, shared_container
from ...shared.database import get_db_session
from .application.policy_integration import TopicPolicyAdapter
from .application.use_cases import (
    TopicBatchApplyUseCase,
    TopicBatchDryRunUseCase,
    TopicDetailUseCase,
    TopicPlanUseCase,
)
from .domain.repositories.interfaces import (
    IAuditRepository,
    ITopicMetadataRepository,
    ITopicRepository,
)
from .infrastructure.kafka_adapter import KafkaTopicAdapter
from .infrastructure.repository.audit_repository import MySQLAuditRepository
from .infrastructure.repository.mysql_repository import MySQLTopicMetadataRepository


class TopicContainer(containers.DeclarativeContainer):
    """Topic 모듈 DI 컨테이너"""

    # 공통 컨테이너에서 설정 가져오기
    config = providers.DependenciesContainer()
    infrastructure = providers.DependenciesContainer()

    # Repositories
    topic_repository: providers.Provider[ITopicRepository] = providers.Singleton(
        KafkaTopicAdapter,
        admin_client=infrastructure.kafka_admin_client,
    )

    # MySQL 기반 구현체들
    metadata_repository: providers.Provider[ITopicMetadataRepository] = providers.Factory(
        MySQLTopicMetadataRepository,
        session=providers.Dependency(),  # 세션은 외부에서 주입
    )

    audit_repository: providers.Provider[IAuditRepository] = providers.Factory(
        MySQLAuditRepository,
        session=providers.Dependency(),  # 세션은 외부에서 주입
    )

    # Policy Integration
    policy_adapter: providers.Provider[TopicPolicyAdapter] = providers.Factory(
        TopicPolicyAdapter,
        policy_service=providers.Factory(
            lambda: policy_use_case_factory.get_policy_evaluation_service()
        ),
    )

    # Use Cases
    dry_run_use_case: providers.Provider[TopicBatchDryRunUseCase] = providers.Factory(
        TopicBatchDryRunUseCase,
        topic_repository=topic_repository,
        metadata_repository=metadata_repository,
        audit_repository=audit_repository,
        policy_adapter=policy_adapter,
    )

    apply_use_case: providers.Provider[TopicBatchApplyUseCase] = providers.Factory(
        TopicBatchApplyUseCase,
        topic_repository=topic_repository,
        metadata_repository=metadata_repository,
        audit_repository=audit_repository,
        policy_adapter=policy_adapter,
    )

    detail_use_case: providers.Provider[TopicDetailUseCase] = providers.Factory(
        TopicDetailUseCase,
        topic_repository=topic_repository,
        metadata_repository=metadata_repository,
    )

    plan_use_case: providers.Provider[TopicPlanUseCase] = providers.Factory(
        TopicPlanUseCase,
        metadata_repository=metadata_repository,
    )


# 전역 컨테이너 인스턴스
container = TopicContainer()

# 공통 컨테이너와 연결
container.config.override(shared_container.config)
container.infrastructure.override(infrastructure_container)


# 의존성 주입 헬퍼 함수들 (세션 관리 개선)
class TopicUseCaseFactory:
    """토픽 유스케이스 팩토리 - 세션 관리 개선"""
    
    def __init__(self) -> None:
        self.topic_repo = container.topic_repository()
        self.policy_adapter = container.policy_adapter()
    
    async def create_dry_run_use_case(self, session: AsyncSession) -> TopicBatchDryRunUseCase:
        """Dry-Run 유스케이스 생성"""
        metadata_repo = MySQLTopicMetadataRepository(session)
        audit_repo = MySQLAuditRepository(session)
        
        return TopicBatchDryRunUseCase(
            topic_repository=self.topic_repo,
            metadata_repository=metadata_repo,
            audit_repository=audit_repo,
            policy_adapter=self.policy_adapter,
        )
    
    async def create_apply_use_case(self, session: AsyncSession) -> TopicBatchApplyUseCase:
        """Apply 유스케이스 생성"""
        metadata_repo = MySQLTopicMetadataRepository(session)
        audit_repo = MySQLAuditRepository(session)
        
        return TopicBatchApplyUseCase(
            topic_repository=self.topic_repo,
            metadata_repository=metadata_repo,
            audit_repository=audit_repo,
            policy_adapter=self.policy_adapter,
        )


# 전역 팩토리 인스턴스
_factory = TopicUseCaseFactory()

# 타입 별칭 (Depends 패턴 개선)
DbSession = Annotated[AsyncSession, Depends(get_db_session)]


async def get_dry_run_use_case(session: DbSession) -> TopicBatchDryRunUseCase:
    """Dry-Run 유스케이스 의존성 (세션 포함)"""
    return await _factory.create_dry_run_use_case(session)


async def get_apply_use_case(session: DbSession) -> TopicBatchApplyUseCase:
    """Apply 유스케이스 의존성 (세션 포함)"""
    return await _factory.create_apply_use_case(session)


def get_detail_use_case(session: DbSession) -> TopicDetailUseCase:
    """Detail 유스케이스 의존성 (세션 포함)"""
    metadata_repo = MySQLTopicMetadataRepository(session)
    topic_repo = container.topic_repository()

    return TopicDetailUseCase(
        topic_repository=topic_repo,
        metadata_repository=metadata_repo,
    )


def get_plan_use_case(session: DbSession) -> TopicPlanUseCase:
    """Plan 유스케이스 의존성 (세션 포함)"""
    metadata_repo = MySQLTopicMetadataRepository(session)

    return TopicPlanUseCase(
        metadata_repository=metadata_repo,
    )


async def get_current_user() -> str:
    """현재 사용자 정보 (개발용 임시)"""
    # 실제 FastAPI 라우터에서는 shared.auth.get_current_user 의존성을 사용
    # 이 함수는 컴테이너 테스트용으로만 사용
    return "dev-user"  # 개발용 임시 사용자
