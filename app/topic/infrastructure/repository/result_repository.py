"""Topic Apply Result Repository - 토픽 적용 결과 저장"""

from __future__ import annotations

import logging
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager

from sqlalchemy.ext.asyncio import AsyncSession

from app.topic.domain.models import DomainTopicApplyResult
from app.topic.infrastructure.models import TopicApplyResultModel

logger = logging.getLogger(__name__)


class ResultRepository:
    """Topic Apply Result 저장 리포지토리 (Session Factory 패턴)"""

    def __init__(
        self, session_factory: Callable[..., AbstractAsyncContextManager[AsyncSession]]
    ) -> None:
        self.session_factory = session_factory

    async def save_apply_result(self, result: DomainTopicApplyResult, applied_by: str) -> None:
        """적용 결과 저장"""
        async with self.session_factory() as session:
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

                session.add(result_model)
                await session.flush()

                logger.info(f"Apply result saved: {result.change_id}")

            except Exception as e:
                logger.error(f"Failed to save apply result {result.change_id}: {e}")
                raise
