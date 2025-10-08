"""Topic MySQL Repository 구현체 - 통합 리포지토리 (Facade 패턴)

3개의 작은 리포지토리(Plan, Result, Metadata)를 조합하여
ITopicMetadataRepository 인터페이스를 구현합니다.
"""

from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.topic.domain.models import (
    ChangeId,
    DomainTopicApplyResult,
    DomainTopicPlan,
    TopicName,
)
from app.topic.domain.repositories.interfaces import ITopicMetadataRepository, PlanMeta

from .metadata_repository import MetadataRepository
from .plan_repository import PlanRepository
from .result_repository import ResultRepository


class MySQLTopicMetadataRepository(ITopicMetadataRepository):
    """MySQL 기반 토픽 메타데이터 리포지토리 - Facade 패턴

    3개의 작은 리포지토리에 작업을 위임하는 통합 리포지토리입니다.
    """

    def __init__(
        self, session_factory: Callable[..., AbstractAsyncContextManager[AsyncSession]]
    ) -> None:
        self.plan_repo = PlanRepository(session_factory)
        self.result_repo = ResultRepository(session_factory)
        self.metadata_repo = MetadataRepository(session_factory)

    # ===== Plan Repository 메서드 위임 =====

    async def save_plan(self, plan: DomainTopicPlan, created_by: str) -> None:
        """계획 저장"""
        await self.plan_repo.save_plan(plan, created_by)

    async def get_plan(self, change_id: ChangeId) -> DomainTopicPlan | None:
        """계획 조회"""
        return await self.plan_repo.get_plan(change_id)

    async def get_plan_meta(self, change_id: ChangeId) -> PlanMeta | None:
        """계획 메타 정보 조회"""
        return await self.plan_repo.get_plan_meta(change_id)

    # ===== Result Repository 메서드 위임 =====

    async def save_apply_result(self, result: DomainTopicApplyResult, applied_by: str) -> None:
        """적용 결과 저장"""
        await self.result_repo.save_apply_result(result, applied_by)

    # ===== Metadata Repository 메서드 위임 =====

    async def get_topic_metadata(self, name: TopicName) -> dict[str, Any] | None:
        """토픽 메타데이터 조회"""
        return await self.metadata_repo.get_topic_metadata(name)

    async def save_topic_metadata(self, name: TopicName, metadata: dict[str, Any]) -> None:
        """토픽 메타데이터 저장"""
        await self.metadata_repo.save_topic_metadata(name, metadata)

    async def delete_topic_metadata(self, name: TopicName) -> None:
        """토픽 메타데이터 삭제"""
        await self.metadata_repo.delete_topic_metadata(name)
