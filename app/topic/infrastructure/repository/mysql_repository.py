"""Topic MySQL Repository 구현체"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.topic.domain.models import (
    ChangeId,
    Environment,
    PlanAction,
    PolicyViolation,
    TopicApplyResult,
    TopicName,
    TopicPlan,
    TopicPlanItem,
)
from app.topic.domain.repositories.interfaces import ITopicMetadataRepository
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

    async def save_plan(self, plan: TopicPlan, created_by: str) -> None:
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
                        "name": v.name,
                        "rule": v.rule,
                        "message": v.message,
                        "severity": v.severity,
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

    async def get_plan(self, change_id: ChangeId) -> TopicPlan | None:
        """계획 조회"""
        try:
            stmt = select(TopicPlanModel).where(TopicPlanModel.change_id == change_id)
            result = await self.session.execute(stmt)
            plan_model = result.scalar_one_or_none()

            if plan_model is None:
                return None

            # JSON 데이터를 TopicPlan 도메인 객체로 역직렬화
            plan_data = plan_model.plan_data

            # 계획 아이템 역직렬화
            items = [
                TopicPlanItem(
                    name=item["name"],
                    action=PlanAction(item["action"]),
                    diff=item["diff"],
                    current_config=item["current_config"],
                    target_config=item["target_config"],
                )
                for item in plan_data["items"]
            ]

            # 정책 위반 역직렬화
            violations = [
                PolicyViolation(
                    name=v["name"],
                    rule=v["rule"],
                    message=v["message"],
                    severity=v["severity"],
                    field=v["field"],
                )
                for v in plan_data["violations"]
            ]

            # Environment enum으로 변환
            env = Environment(plan_data["env"])

            return TopicPlan(
                change_id=plan_data["change_id"],
                env=env,
                items=tuple(items),
                violations=tuple(violations),
            )

        except Exception as e:
            logger.error(f"Failed to get plan {change_id}: {e}")
            raise

    async def save_apply_result(self, result: TopicApplyResult, applied_by: str) -> None:
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
            metadata_model = result.scalar_one_or_none()

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
            existing = result.scalar_one_or_none()

            if existing:
                # 업데이트
                existing.owner = metadata.get("owner")
                existing.sla = metadata.get("sla")
                existing.doc = metadata.get("doc")
                existing.tags = metadata.get("tags", {})
                existing.config = metadata.get("config", {})
                existing.updated_by = "system"  # TODO: 실제 사용자 정보
            else:
                # 새로 생성
                metadata_model = TopicMetadataModel(
                    topic_name=name,
                    owner=metadata.get("owner"),
                    sla=metadata.get("sla"),
                    doc=metadata.get("doc"),
                    tags=metadata.get("tags", {}),
                    config=metadata.get("config", {}),
                    created_by="system",  # TODO: 실제 사용자 정보
                    updated_by="system",  # TODO: 실제 사용자 정보
                )
                self.session.add(metadata_model)

            await self.session.flush()
            logger.info(f"Topic metadata saved: {name}")

        except Exception as e:
            logger.error(f"Failed to save topic metadata {name}: {e}")
            raise


# 이 팩토리 함수는 더 이상 사용하지 않음 (컨테이너에서 직접 관리)
# async def get_mysql_topic_metadata_repository() -> MySQLTopicMetadataRepository:
#     """MySQL 토픽 메타데이터 리포지토리 팩토리"""
#     async with get_db_session() as session:
#         return MySQLTopicMetadataRepository(session)
