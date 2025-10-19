"""Topic Plan Repository - 토픽 계획 저장/조회"""

from __future__ import annotations

import inspect
import logging
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.domain.policy_types import (
    DomainPolicySeverity,
    DomainPolicyViolation,
    DomainResourceType,
)
from app.topic.domain.models import (
    ChangeId,
    DomainEnvironment,
    DomainPlanAction,
    DomainTopicPlan,
    DomainTopicPlanItem,
)
from app.topic.domain.repositories.interfaces import PlanMeta
from app.topic.infrastructure.models import TopicApplyResultModel, TopicPlanModel

logger = logging.getLogger(__name__)


class PlanRepository:
    """Topic Plan 저장/조회 리포지토리 (Session Factory 패턴)"""

    def __init__(
        self, session_factory: Callable[..., AbstractAsyncContextManager[AsyncSession]]
    ) -> None:
        self.session_factory = session_factory

    @staticmethod
    async def _maybe_await(value: Any) -> Any:
        """테스트에서 AsyncMock이 반환한 awaitable을 안전하게 처리"""
        return await value if inspect.isawaitable(value) else value

    async def save_plan(self, plan: DomainTopicPlan, created_by: str) -> None:
        """계획 저장 (UPSERT: 동일 change_id면 업데이트)"""
        async with self.session_factory() as session:
            try:
                # TopicPlan 도메인 객체를 JSON으로 직렬화
                plan_data = {
                    "change_id": plan.change_id,
                    "env": plan.env.value,
                    "items": [
                        {
                            "name": item.name,
                            "action": item.action.value,
                            "diff": item.diff,
                            "current_config": item.current_config,
                            "target_config": item.target_config,
                        }
                        for item in plan.items
                    ],
                    "violations": [
                        {
                            "resource_name": v.resource_name,
                            "rule_id": v.rule_id,
                            "message": v.message,
                            "severity": v.severity.value,
                            "field": v.field,
                        }
                        for v in plan.violations
                    ],
                }

                # UPSERT: 동일 change_id가 있으면 업데이트
                insert_stmt = mysql_insert(TopicPlanModel).values(
                    change_id=plan.change_id,
                    env=plan.env.value,
                    plan_data=plan_data,
                    can_apply=plan.can_apply,
                    created_by=created_by,
                )

                # ON DUPLICATE KEY UPDATE
                upsert_stmt = insert_stmt.on_duplicate_key_update(
                    env=insert_stmt.inserted.env,
                    plan_data=insert_stmt.inserted.plan_data,
                    can_apply=insert_stmt.inserted.can_apply,
                    status="pending",  # 다시 pending으로 초기화
                    updated_by=created_by,
                )

                await session.execute(upsert_stmt)
                await session.flush()

                logger.info(f"Plan saved: {plan.change_id}")

            except Exception as e:
                logger.error(f"Failed to save plan {plan.change_id}: {e}")
                raise

    async def get_plan(self, change_id: ChangeId) -> DomainTopicPlan | None:
        """계획 조회"""
        async with self.session_factory() as session:
            try:
                stmt = select(TopicPlanModel).where(TopicPlanModel.change_id == change_id)
                result = await session.execute(stmt)
                plan_model = await self._maybe_await(result.scalar_one_or_none())

                if plan_model is None:
                    return None

                # JSON 데이터를 TopicPlan 도메인 객체로 역직렬화
                plan_data = plan_model.plan_data

                # 계획 아이템 역직렬화
                items = [
                    DomainTopicPlanItem(
                        name=item["name"],
                        action=DomainPlanAction(item["action"]),
                        diff=item["diff"],
                        current_config=item["current_config"],
                        target_config=item["target_config"],
                    )
                    for item in plan_data["items"]
                ]

                # 정책 위반 역직렬화
                violations = [
                    DomainPolicyViolation(
                        resource_type=DomainResourceType.TOPIC,
                        resource_name=v["resource_name"],
                        rule_id=v["rule_id"],
                        message=v["message"],
                        severity=DomainPolicySeverity(v["severity"]),
                        field=v.get("field"),
                    )
                    for v in plan_data.get("violations", [])
                ]

                # Environment enum으로 변환
                env = DomainEnvironment(plan_data["env"])

                return DomainTopicPlan(
                    change_id=plan_data["change_id"],
                    env=env,
                    items=tuple(items),
                    violations=tuple(violations),
                )

            except Exception as e:
                logger.error(f"Failed to get plan {change_id}: {e}")
                raise

    async def get_plan_meta(self, change_id: ChangeId) -> PlanMeta | None:
        """계획 메타 정보 조회 (상태/타임스탬프)"""
        async with self.session_factory() as session:
            try:
                # 계획 기본 메타 정보 조회
                stmt = select(TopicPlanModel).where(TopicPlanModel.change_id == change_id)
                result = await session.execute(stmt)
                plan_model = result.scalar_one_or_none()

                if plan_model is None:
                    return None

                created_at = plan_model.created_at.isoformat()
                status = plan_model.status

                # 적용 여부/시간 조회 (있을 때만)
                stmt2 = select(TopicApplyResultModel).where(
                    TopicApplyResultModel.change_id == change_id
                )
                result2 = await session.execute(stmt2)
                apply_model = await self._maybe_await(result2.scalar_one_or_none())
                applied_at = apply_model.applied_at.isoformat() if apply_model else None

                return PlanMeta(status=status, created_at=created_at, applied_at=applied_at)

            except Exception as e:
                logger.error(f"Failed to get plan meta {change_id}: {e}")
                raise
