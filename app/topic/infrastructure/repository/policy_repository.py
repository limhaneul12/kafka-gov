"""Policy Repository - 정책 CRUD 및 버전 관리"""

from __future__ import annotations

import inspect
import logging
import uuid
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from typing import Any

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.topic.domain.policies.management import PolicyStatus, PolicyType, StoredPolicy
from app.topic.domain.repositories import IPolicyRepository
from app.topic.infrastructure.models import PolicyModel

logger = logging.getLogger(__name__)


class PolicyRepository(IPolicyRepository):
    """정책 저장/조회/버전관리 리포지토리"""

    def __init__(
        self, session_factory: Callable[..., AbstractAsyncContextManager[AsyncSession]]
    ) -> None:
        self.session_factory = session_factory

    @staticmethod
    async def _maybe_await(value: Any) -> Any:
        """테스트에서 AsyncMock이 반환한 awaitable을 안전하게 처리"""
        return await value if inspect.isawaitable(value) else value

    def _model_to_domain(self, model: PolicyModel) -> StoredPolicy:
        """ORM 모델 → Domain 모델 변환"""
        return StoredPolicy(
            policy_id=model.policy_id,
            policy_type=PolicyType(model.policy_type),
            name=model.name,
            description=model.description,
            version=model.version,
            status=PolicyStatus(model.status),
            content=model.content,
            created_by=model.created_by,
            created_at=model.created_at.isoformat(),
            updated_at=model.updated_at.isoformat() if model.updated_at else None,
        )

    async def create_policy(
        self,
        policy_type: PolicyType,
        name: str,
        description: str,
        content: dict,
        created_by: str,
    ) -> StoredPolicy:
        """새 정책 생성 (version=1, status=DRAFT)"""
        async with self.session_factory() as session:
            # 새 UUID 생성
            policy_id = str(uuid.uuid4())

            # 새 정책 생성
            model = PolicyModel(
                policy_id=policy_id,
                version=1,
                policy_type=policy_type.value,
                name=name,
                description=description,
                status=PolicyStatus.DRAFT.value,
                content=content,
                created_by=created_by,
            )

            session.add(model)
            await session.commit()
            await session.refresh(model)

            logger.info(f"Created policy: {policy_id} v1 ({policy_type.value})")
            return self._model_to_domain(model)

    async def get_policy(self, policy_id: str, version: int | None = None) -> StoredPolicy | None:
        """정책 조회 (version 지정 가능)

        Args:
            policy_id: 정책 ID
            version: 버전 번호 (None이면 최신 버전)
        """
        async with self.session_factory() as session:
            if version is not None:
                # 특정 버전 조회
                stmt = select(PolicyModel).where(
                    PolicyModel.policy_id == policy_id, PolicyModel.version == version
                )
            else:
                # 최신 버전 조회
                stmt = (
                    select(PolicyModel)
                    .where(PolicyModel.policy_id == policy_id)
                    .order_by(desc(PolicyModel.version))
                    .limit(1)
                )

            result = await session.execute(stmt)
            model = await self._maybe_await(result.scalar_one_or_none())

            if model is None:
                logger.debug(f"Policy not found: {policy_id} (version={version})")
                return None

            return self._model_to_domain(model)

    async def get_active_policy(self, policy_id: str) -> StoredPolicy | None:
        """활성 정책 조회 (status=ACTIVE)"""
        async with self.session_factory() as session:
            stmt = select(PolicyModel).where(
                PolicyModel.policy_id == policy_id, PolicyModel.status == PolicyStatus.ACTIVE.value
            )

            result = await session.execute(stmt)
            model = await self._maybe_await(result.scalar_one_or_none())

            if model is None:
                logger.debug(f"Active policy not found: {policy_id}")
                return None

            return self._model_to_domain(model)

    async def list_policies(
        self,
        policy_type: PolicyType | None = None,
        status: PolicyStatus | None = None,
    ) -> list[StoredPolicy]:
        """정책 목록 조회 (최신 버전만)"""
        async with self.session_factory() as session:
            # 서브쿼리: 각 policy_id별 최대 버전
            subq = (
                select(PolicyModel.policy_id, func.max(PolicyModel.version).label("max_version"))
                .group_by(PolicyModel.policy_id)
                .subquery()
            )

            # 메인 쿼리: 최신 버전만 조회
            stmt = select(PolicyModel).join(
                subq,
                (PolicyModel.policy_id == subq.c.policy_id)
                & (PolicyModel.version == subq.c.max_version),
            )

            # 필터 적용
            if policy_type:
                stmt = stmt.where(PolicyModel.policy_type == policy_type.value)
            if status:
                stmt = stmt.where(PolicyModel.status == status.value)

            result = await session.execute(stmt)
            models = await self._maybe_await(result.scalars().all())

            return [self._model_to_domain(m) for m in models]

    async def list_policy_versions(self, policy_id: str) -> list[StoredPolicy]:
        """특정 정책의 모든 버전 조회 (버전 히스토리)"""
        async with self.session_factory() as session:
            stmt = (
                select(PolicyModel)
                .where(PolicyModel.policy_id == policy_id)
                .order_by(desc(PolicyModel.version))
            )

            result = await session.execute(stmt)
            models = await self._maybe_await(result.scalars().all())

            if not models:
                logger.debug(f"No versions found for policy: {policy_id}")
                return []

            return [self._model_to_domain(m) for m in models]

    async def update_policy(
        self,
        policy_id: str,
        name: str | None = None,
        description: str | None = None,
        content: dict | None = None,
    ) -> StoredPolicy:
        """정책 업데이트 (새 버전 생성, status=DRAFT)"""
        async with self.session_factory() as session:
            # 1. 현재 최대 버전 조회
            stmt = select(func.max(PolicyModel.version)).where(PolicyModel.policy_id == policy_id)
            result = await session.execute(stmt)
            max_version = await self._maybe_await(result.scalar())

            if max_version is None:
                raise ValueError(f"Policy not found: {policy_id}")

            # 2. 기존 정책 조회 (기본값 복사용)
            stmt = (
                select(PolicyModel)
                .where(PolicyModel.policy_id == policy_id)
                .order_by(desc(PolicyModel.version))
                .limit(1)
            )
            result = await session.execute(stmt)
            old_model = await self._maybe_await(result.scalar_one())

            # 3. 새 버전 생성
            new_version = max_version + 1
            new_model = PolicyModel(
                policy_id=policy_id,
                version=new_version,
                policy_type=old_model.policy_type,
                name=name if name is not None else old_model.name,
                description=description if description is not None else old_model.description,
                status=PolicyStatus.DRAFT.value,
                content=content if content is not None else old_model.content,
                created_by="system",  # 업데이트는 시스템으로 표시
            )

            session.add(new_model)
            await session.commit()
            await session.refresh(new_model)

            logger.info(f"Updated policy: {policy_id} v{new_version} (DRAFT)")
            return self._model_to_domain(new_model)

    async def activate_policy(self, policy_id: str, version: int | None = None) -> StoredPolicy:
        """정책 활성화 (DRAFT → ACTIVE)

        Args:
            policy_id: 정책 ID
            version: 활성화할 버전 (None이면 최신 DRAFT)
        """
        async with self.session_factory() as session:
            # 1. 기존 ACTIVE 버전 → ARCHIVED
            stmt = select(PolicyModel).where(
                PolicyModel.policy_id == policy_id, PolicyModel.status == PolicyStatus.ACTIVE.value
            )
            result = await session.execute(stmt)
            active_models = await self._maybe_await(result.scalars().all())

            for model in active_models:
                model.status = PolicyStatus.ARCHIVED.value

            # 2. 활성화할 DRAFT 조회
            if version is not None:
                stmt = select(PolicyModel).where(
                    PolicyModel.policy_id == policy_id,
                    PolicyModel.version == version,
                    PolicyModel.status == PolicyStatus.DRAFT.value,
                )
            else:
                stmt = (
                    select(PolicyModel)
                    .where(
                        PolicyModel.policy_id == policy_id,
                        PolicyModel.status == PolicyStatus.DRAFT.value,
                    )
                    .order_by(desc(PolicyModel.version))
                    .limit(1)
                )

            result = await session.execute(stmt)
            draft_model = await self._maybe_await(result.scalar_one_or_none())

            if draft_model is None:
                raise ValueError(f"No draft policy found: {policy_id} (version={version})")

            # 3. DRAFT → ACTIVE
            draft_model.status = PolicyStatus.ACTIVE.value

            await session.commit()
            await session.refresh(draft_model)

            logger.info(f"Activated policy: {policy_id} v{draft_model.version}")
            return self._model_to_domain(draft_model)

    async def archive_policy(self, policy_id: str) -> StoredPolicy:
        """정책 보관 (ACTIVE → ARCHIVED)"""
        async with self.session_factory() as session:
            stmt = select(PolicyModel).where(
                PolicyModel.policy_id == policy_id, PolicyModel.status == PolicyStatus.ACTIVE.value
            )

            result = await session.execute(stmt)
            model = await self._maybe_await(result.scalar_one_or_none())

            if model is None:
                raise ValueError(f"No active policy found: {policy_id}")

            model.status = PolicyStatus.ARCHIVED.value

            await session.commit()
            await session.refresh(model)

            logger.info(f"Archived policy: {policy_id} v{model.version}")
            return self._model_to_domain(model)

    async def delete_policy(self, policy_id: str, version: int | None = None) -> None:
        """정책 삭제 (DRAFT만 삭제 가능)

        Args:
            policy_id: 정책 ID
            version: 삭제할 버전 (None이면 모든 DRAFT 버전 삭제)
        """
        async with self.session_factory() as session:
            if version is not None:
                # 특정 버전 삭제
                stmt = select(PolicyModel).where(
                    PolicyModel.policy_id == policy_id, PolicyModel.version == version
                )
                result = await session.execute(stmt)
                model = await self._maybe_await(result.scalar_one_or_none())

                if model is None:
                    raise ValueError(f"Policy not found: {policy_id} v{version}")

                if model.status != PolicyStatus.DRAFT.value:
                    raise ValueError(
                        f"Cannot delete non-draft policy: {policy_id} v{version} (status={model.status})"
                    )

                await session.delete(model)
                logger.info(f"Deleted policy: {policy_id} v{version}")
            else:
                # 모든 DRAFT 버전 삭제
                stmt = select(PolicyModel).where(
                    PolicyModel.policy_id == policy_id,
                    PolicyModel.status == PolicyStatus.DRAFT.value,
                )
                result = await session.execute(stmt)
                models = await self._maybe_await(result.scalars().all())

                if not models:
                    raise ValueError(f"No draft policies found: {policy_id}")

                for model in models:
                    await session.delete(model)

                logger.info(f"Deleted {len(models)} draft policies: {policy_id}")

            await session.commit()

    async def rollback_to_version(self, policy_id: str, target_version: int) -> StoredPolicy:
        """이전 버전으로 롤백 (이전 버전 복사 → 새 DRAFT 생성)

        Args:
            policy_id: 정책 ID
            target_version: 롤백할 대상 버전

        Returns:
            새로 생성된 DRAFT 정책
        """
        async with self.session_factory() as session:
            # 1. 대상 버전 조회
            stmt = select(PolicyModel).where(
                PolicyModel.policy_id == policy_id, PolicyModel.version == target_version
            )
            result = await session.execute(stmt)
            target_model = await self._maybe_await(result.scalar_one_or_none())

            if target_model is None:
                raise ValueError(f"Target version not found: {policy_id} v{target_version}")

            # 2. 현재 최대 버전 조회
            stmt = select(func.max(PolicyModel.version)).where(PolicyModel.policy_id == policy_id)
            result = await session.execute(stmt)
            max_version = await self._maybe_await(result.scalar())

            # 3. 새 버전 생성 (대상 버전의 content 복사)
            new_version = max_version + 1
            new_model = PolicyModel(
                policy_id=policy_id,
                version=new_version,
                policy_type=target_model.policy_type,
                name=target_model.name,
                description=f"{target_model.description} (롤백: v{target_version})",
                status=PolicyStatus.DRAFT.value,
                content=target_model.content,  # ← content 복사
                created_by="system",
            )

            session.add(new_model)
            await session.commit()
            await session.refresh(new_model)

            logger.info(
                f"Rolled back policy: {policy_id} v{target_version} → v{new_version} (DRAFT)"
            )
            return self._model_to_domain(new_model)
