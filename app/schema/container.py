"""Schema 모듈 DI 컨테이너"""

from __future__ import annotations

from typing import Annotated

from dependency_injector import containers, providers
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..shared.container import infrastructure_container, shared_container
from ..shared.database import get_db_session
from .application.use_cases import (
    SchemaBatchApplyUseCase,
    SchemaBatchDryRunUseCase,
    SchemaPlanUseCase,
    SchemaUploadUseCase,
)
from .domain.policies import SchemaPolicyEngine
from .domain.repositories.interfaces import (
    IObjectStorageRepository,
    ISchemaAuditRepository,
    ISchemaMetadataRepository,
    ISchemaRegistryRepository,
)
from .infrastructure.repository.audit_repository import MySQLSchemaAuditRepository
from .infrastructure.repository.mysql_repository import MySQLSchemaMetadataRepository
from .infrastructure.schema_registry_adapter import ConfluentSchemaRegistryAdapter
from .infrastructure.storage.minio_adapter import create_minio_storage_adapter


class SchemaContainer(containers.DeclarativeContainer):
    """Schema 모듈 DI 컨테이너"""

    # 공통 컨테이너에서 설정 가져오기
    config = providers.DependenciesContainer()
    infrastructure = providers.DependenciesContainer()

    # Repositories
    schema_registry_repository: providers.Provider[ISchemaRegistryRepository] = providers.Singleton(
        ConfluentSchemaRegistryAdapter,
        client=infrastructure.schema_registry_client,
    )

    # MySQL 기반 구현체들 (팩토리 함수 사용)
    metadata_repository: providers.Provider[ISchemaMetadataRepository] = providers.Factory(
        MySQLSchemaMetadataRepository,  # type: ignore[arg-type]
        session=providers.Dependency(),  # 세션은 외부에서 주입
    )

    audit_repository: providers.Provider[ISchemaAuditRepository] = providers.Factory(
        MySQLSchemaAuditRepository,  # type: ignore[arg-type]
        session=providers.Dependency(),  # 세션은 외부에서 주입
    )

    # Object Storage (MinIO)
    object_storage_repository: providers.Provider[IObjectStorageRepository] = providers.Singleton(
        create_minio_storage_adapter,
        client=infrastructure.minio_client,
        bucket_name=config.storage_bucket_name,
        base_url=config.storage_base_url,
    )

    # Domain Services
    policy_engine: providers.Provider[SchemaPolicyEngine] = providers.Singleton(SchemaPolicyEngine)

    # Use Cases
    dry_run_use_case: providers.Provider[SchemaBatchDryRunUseCase] = providers.Factory(
        SchemaBatchDryRunUseCase,
        registry_repository=schema_registry_repository,
        metadata_repository=metadata_repository,
        audit_repository=audit_repository,
        policy_engine=policy_engine,
    )

    apply_use_case: providers.Provider[SchemaBatchApplyUseCase] = providers.Factory(
        SchemaBatchApplyUseCase,
        registry_repository=schema_registry_repository,
        metadata_repository=metadata_repository,
        audit_repository=audit_repository,
        storage_repository=object_storage_repository,
        policy_engine=policy_engine,
    )

    plan_use_case: providers.Provider[SchemaPlanUseCase] = providers.Factory(
        SchemaPlanUseCase,
        metadata_repository=metadata_repository,
    )

    upload_use_case: providers.Provider[SchemaUploadUseCase] = providers.Factory(
        SchemaUploadUseCase,
        storage_repository=object_storage_repository,
        metadata_repository=metadata_repository,
        audit_repository=audit_repository,
    )


# 전역 컨테이너 인스턴스
container = SchemaContainer()

# 공통 컨테이너와 연결
container.config.override(shared_container)
container.infrastructure.override(infrastructure_container)


# 타입 별칭 (Depends 패턴)
DbSession = Annotated[AsyncSession, Depends(get_db_session)]


async def get_schema_dry_run_use_case(session: DbSession) -> SchemaBatchDryRunUseCase:
    """SchemaBatchDryRunUseCase 의존성 (세션 포함)"""
    metadata_repo = MySQLSchemaMetadataRepository(session)
    audit_repo = MySQLSchemaAuditRepository(session)
    return SchemaBatchDryRunUseCase(
        registry_repository=container.schema_registry_repository(),
        metadata_repository=metadata_repo,  # type: ignore[arg-type]
        audit_repository=audit_repo,  # type: ignore[arg-type]
        policy_engine=container.policy_engine(),
    )


async def get_schema_apply_use_case(session: DbSession) -> SchemaBatchApplyUseCase:
    """SchemaBatchApplyUseCase 의존성 (세션 포함)"""
    metadata_repo = MySQLSchemaMetadataRepository(session)
    audit_repo = MySQLSchemaAuditRepository(session)
    return SchemaBatchApplyUseCase(
        registry_repository=container.schema_registry_repository(),
        metadata_repository=metadata_repo,  # type: ignore[arg-type]
        audit_repository=audit_repo,  # type: ignore[arg-type]
        storage_repository=container.object_storage_repository(),
        policy_engine=container.policy_engine(),
    )


async def get_schema_upload_use_case(session: DbSession) -> SchemaUploadUseCase:
    """SchemaUploadUseCase 의존성 (세션 포함)"""
    metadata_repo = MySQLSchemaMetadataRepository(session)
    audit_repo = MySQLSchemaAuditRepository(session)
    return SchemaUploadUseCase(
        storage_repository=container.object_storage_repository(),
        metadata_repository=metadata_repo,  # type: ignore[arg-type]
        audit_repository=audit_repo,  # type: ignore[arg-type]
    )


def get_schema_plan_use_case(session: DbSession) -> SchemaPlanUseCase:
    """SchemaPlanUseCase 의존성 (세션 포함)"""
    metadata_repo = MySQLSchemaMetadataRepository(session)
    return SchemaPlanUseCase(
        metadata_repository=metadata_repo,  # type: ignore[arg-type]
    )
