"""Topic MySQL Repository 구현체"""

from __future__ import annotations

import inspect
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.policy import DomainPolicySeverity, DomainResourceType
from app.topic.domain.models import (
    ChangeId,
    DomainEnvironment,
    DomainPlanAction,
    DomainPolicyViolation,
    DomainTopicApplyResult,
    DomainTopicPlan,
    DomainTopicPlanItem,
    TopicName,
)
from app.topic.domain.repositories.interfaces import ITopicMetadataRepository, PlanMeta
from app.topic.infrastructure.models import (
    TopicApplyResultModel,
    TopicMetadataModel,
    TopicPlanModel,
)

logger = logging.getLogger(__name__)


class MySQLTopicMetadataRepository(ITopicMetadataRepository):
    """MySQL 기반 토픽 메타데이터 리포지토리"""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    async def _maybe_await(value: Any) -> Any:
        """테스트에서 AsyncMock이 반환한 awaitable을 안전하게 처리.
        프로덕션 경로에서는 동기 객체가 오므로 오버헤드는 사실상 없음.
        """
        return await value if inspect.isawaitable(value) else value

    async def save_plan(self, plan: DomainTopicPlan, created_by: str) -> None:
        """계획 저장"""
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

            plan_model = TopicPlanModel(
                change_id=plan.change_id,
                env=plan.env.value,
                plan_data=plan_data,
                can_apply=plan.can_apply,
                created_by=created_by,
            )

            self.session.add(plan_model)
            await self.session.flush()

            logger.info(f"Plan saved: {plan.change_id}")

        except Exception as e:
            logger.error(f"Failed to save plan {plan.change_id}: {e}")
            raise

    async def get_plan(self, change_id: ChangeId) -> DomainTopicPlan | None:
        """계획 조회"""
        try:
            stmt = select(TopicPlanModel).where(TopicPlanModel.change_id == change_id)
            result = await self.session.execute(stmt)
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
        try:
            # 계획 기본 메타 정보 조회
            stmt = select(TopicPlanModel).where(TopicPlanModel.change_id == change_id)
            result = await self.session.execute(stmt)
            plan_model = result.scalar_one_or_none()

            if plan_model is None:
                return None

            created_at = plan_model.created_at.isoformat()
            status = plan_model.status

            # 적용 여부/시간 조회 (있을 때만)
            stmt2 = select(TopicApplyResultModel).where(
                TopicApplyResultModel.change_id == change_id
            )
            result2 = await self.session.execute(stmt2)
            apply_model = await self._maybe_await(result2.scalar_one_or_none())
            applied_at = apply_model.applied_at.isoformat() if apply_model else None

            return PlanMeta(status=status, created_at=created_at, applied_at=applied_at)

        except Exception as e:
            logger.error(f"Failed to get plan meta {change_id}: {e}")
            raise

    async def save_apply_result(self, result: DomainTopicApplyResult, applied_by: str) -> None:
        """적용 결과 저장"""
        try:
            # TopicApplyResult 도메인 객체를 JSON으로 직렬화
            result_data = {
                "change_id": result.change_id,
                "env": result.env.value,
                "applied": list(result.applied),
                "skipped": list(result.skipped),
                "failed": [
                    {
                        "name": failed_item.get("name", "unknown"),
                        "error": failed_item.get("error", "unknown error"),
                    }
                    for failed_item in result.failed
                ],
                "audit_id": result.audit_id,
                "summary": result.summary(),
            }

            success_count = len(result.applied)
            failure_count = len(result.failed)

            result_model = TopicApplyResultModel(
                change_id=result.change_id,
                result_data=result_data,
                success_count=success_count,
                failure_count=failure_count,
                applied_by=applied_by,
            )

            self.session.add(result_model)
            await self.session.flush()

            logger.info(f"Apply result saved: {result.change_id}")

        except Exception as e:
            logger.error(f"Failed to save apply result {result.change_id}: {e}")
            raise

    async def get_topic_metadata(self, name: TopicName) -> dict[str, Any] | None:
        """토픽 메타데이터 조회"""
        try:
            stmt = select(TopicMetadataModel).where(TopicMetadataModel.topic_name == name)
            result = await self.session.execute(stmt)
            metadata_model = await self._maybe_await(result.scalar_one_or_none())

            if metadata_model is None:
                return None

            return {
                "owner": metadata_model.owner,
                "sla": metadata_model.sla,
                "doc": metadata_model.doc,
                "tags": metadata_model.tags or {},
                "config": metadata_model.config or {},
                "created_by": metadata_model.created_by,
                "updated_by": metadata_model.updated_by,
                "created_at": metadata_model.created_at.isoformat(),
                "updated_at": metadata_model.updated_at.isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to get topic metadata {name}: {e}")
            raise

    async def save_topic_metadata(self, name: TopicName, metadata: dict[str, Any]) -> None:
        """토픽 메타데이터 저장"""
        try:
            # 기존 메타데이터 조회
            stmt = select(TopicMetadataModel).where(TopicMetadataModel.topic_name == name)
            result = await self.session.execute(stmt)
            existing = await self._maybe_await(result.scalar_one_or_none())

            if existing:
                # 업데이트 후 merge 적용
                existing.owner = metadata.get("owner")
                existing.sla = metadata.get("sla")
                existing.doc = metadata.get("doc")
                existing.tags = metadata.get("tags", {})
                existing.config = metadata.get("config", {})
                existing.updated_by = "system"
                await self.session.merge(existing)
            else:
                # 새로 생성 - merge로 upsert
                metadata_model = TopicMetadataModel(
                    topic_name=name,
                    owner=metadata.get("owner"),
                    sla=metadata.get("sla"),
                    doc=metadata.get("doc"),
                    tags=metadata.get("tags", {}),
                    config=metadata.get("config", {}),
                    created_by="system",
                    updated_by="system",
                )
                await self.session.merge(metadata_model)

            await self.session.flush()
            logger.info(f"Topic metadata saved: {name}")

        except Exception as e:
            logger.error(f"Failed to save topic metadata {name}: {e}")
            raise
