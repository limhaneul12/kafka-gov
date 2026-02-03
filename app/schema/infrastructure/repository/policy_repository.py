"""Schema MySQL Policy Repository 구현체"""

from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.schema.domain.models.policy_management import (
    DomainSchemaPolicy,
    SchemaPolicyStatus,
    SchemaPolicyType,
)
from app.schema.domain.repositories.interfaces import ISchemaPolicyRepository
from app.schema.infrastructure.models import SchemaPolicyModel


class MySQLSchemaPolicyRepository(ISchemaPolicyRepository):
    """MySQL 기반 스키마 정책 리포지토리"""

    def __init__(
        self, session_factory: Callable[..., AbstractAsyncContextManager[AsyncSession]]
    ) -> None:
        self.session_factory = session_factory

    async def save(self, policy: DomainSchemaPolicy) -> None:
        """정책 저장 (버전 관리 포함)"""
        async with self.session_factory() as session:
            model = SchemaPolicyModel(
                policy_id=policy.policy_id,
                version=policy.version,
                policy_type=policy.policy_type.value,
                name=policy.name,
                description=policy.description,
                status=policy.status.value,
                content=policy.content,
                target_environment=policy.target_environment,
                created_by=policy.created_by,
                created_at=datetime.fromisoformat(policy.created_at)
                if policy.created_at
                else datetime.now(),
            )
            session.add(model)
            await session.flush()

    async def get_by_id(
        self, policy_id: str, version: int | None = None
    ) -> DomainSchemaPolicy | None:
        """특정 ID와 버전의 정책 조회 (버전 생략 시 최신 버전)"""
        async with self.session_factory() as session:
            stmt = select(SchemaPolicyModel).where(SchemaPolicyModel.policy_id == policy_id)
            if version:
                stmt = stmt.where(SchemaPolicyModel.version == version)
            else:
                stmt = stmt.order_by(SchemaPolicyModel.version.desc()).limit(1)

            result = await session.execute(stmt)
            model = result.scalar_one_or_none()

            if not model:
                return None

            return self._to_domain(model)

    async def list_active_policies(
        self, env: str | None = None, policy_type: SchemaPolicyType | None = None
    ) -> list[DomainSchemaPolicy]:
        """활성화된 정책 목록 조회"""
        async with self.session_factory() as session:
            stmt = select(SchemaPolicyModel).where(
                SchemaPolicyModel.status == SchemaPolicyStatus.ACTIVE.value
            )

            if env and env != "total":
                stmt = stmt.where(SchemaPolicyModel.target_environment.in_([env, "total"]))

            if policy_type:
                stmt = stmt.where(SchemaPolicyModel.policy_type == policy_type.value)

            result = await session.execute(stmt)
            models = result.scalars().all()

            return [self._to_domain(m) for m in models]

    async def list_all_policies(
        self, env: str | None = None, policy_type: SchemaPolicyType | None = None
    ) -> list[DomainSchemaPolicy]:
        """모든 정책 목록 조회 (상태 무관)"""
        async with self.session_factory() as session:
            stmt = select(SchemaPolicyModel)

            if env and env != "total":
                stmt = stmt.where(SchemaPolicyModel.target_environment.in_([env, "total"]))

            if policy_type:
                stmt = stmt.where(SchemaPolicyModel.policy_type == policy_type.value)

            result = await session.execute(stmt)
            models = result.scalars().all()

            return [self._to_domain(m) for m in models]

    async def get_history(self, policy_id: str) -> list[DomainSchemaPolicy]:
        """정책의 모든 버전 이력 조회"""
        async with self.session_factory() as session:
            stmt = (
                select(SchemaPolicyModel)
                .where(SchemaPolicyModel.policy_id == policy_id)
                .order_by(SchemaPolicyModel.version.desc())
            )

            result = await session.execute(stmt)
            models = result.scalars().all()

            return [self._to_domain(m) for m in models]

    async def update_status(self, policy_id: str, version: int, status: SchemaPolicyStatus) -> None:
        """정책 상태 업데이트"""
        async with self.session_factory() as session:
            stmt = select(SchemaPolicyModel).where(
                SchemaPolicyModel.policy_id == policy_id, SchemaPolicyModel.version == version
            )
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()

            if model:
                model.status = status.value
                if status == SchemaPolicyStatus.ACTIVE:
                    model.activated_at = datetime.now()
                await session.flush()

    async def delete_policy(self, policy_id: str) -> None:
        """정책의 모든 버전 삭제"""
        async with self.session_factory() as session:
            stmt = delete(SchemaPolicyModel).where(SchemaPolicyModel.policy_id == policy_id)
            await session.execute(stmt)
            await session.flush()

    async def delete_version(self, policy_id: str, version: int) -> None:
        """정책의 특정 버전 삭제"""
        async with self.session_factory() as session:
            stmt = delete(SchemaPolicyModel).where(
                SchemaPolicyModel.policy_id == policy_id, SchemaPolicyModel.version == version
            )
            await session.execute(stmt)
            await session.flush()

    def _to_domain(self, model: SchemaPolicyModel) -> DomainSchemaPolicy:
        """Internal helper to convert ORM to Domain model"""
        return DomainSchemaPolicy(
            policy_id=model.policy_id,
            policy_type=SchemaPolicyType(model.policy_type),
            name=model.name,
            description=model.description,
            version=model.version,
            status=SchemaPolicyStatus(model.status),
            content=model.content,
            target_environment=model.target_environment,
            created_by=model.created_by,
            created_at=model.created_at.isoformat(),
            updated_at=model.updated_at.isoformat() if model.updated_at else None,
            activated_at=model.activated_at.isoformat() if model.activated_at else None,
        )
