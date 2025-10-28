"""List Consumer Groups Use Case

Consumer Group 목록 조회

책임:
- DB에서 최신 스냅샷 조회
- Domain Model → Response DTO 변환
"""

from collections.abc import Callable
from contextlib import AbstractAsyncContextManager

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.consumer.infrastructure.models import ConsumerGroupSnapshotModel
from app.consumer.interface.schema import (
    ConsumerGroupListResponse,
    ConsumerGroupResponse,
    LagStatsResponse,
)


class ListConsumerGroupsUseCase:
    """Consumer Group 목록 조회 Use Case

    사용 예시:
    ```python
    use_case = ListConsumerGroupsUseCase(session)
    response = await use_case.execute(cluster_id)
    ```
    """

    def __init__(
        self, session_factory: Callable[[], AbstractAsyncContextManager[AsyncSession]]
    ) -> None:
        """Use case 생성자

        Args:
            session_factory: AsyncSession을 생성하는 비동기 컨텍스트 팩토리
        """
        self._session_factory = session_factory

    async def execute(self, cluster_id: str) -> ConsumerGroupListResponse:
        """Consumer Group 목록 조회

        Args:
            cluster_id: 클러스터 ID

        Returns:
            ConsumerGroupListResponse
        """
        # 1. 최신 스냅샷 조회 (group_id별로 최신 1개씩)
        # Subquery: 각 group_id별 최대 ts

        subq = (
            select(
                ConsumerGroupSnapshotModel.group_id,
                func.max(ConsumerGroupSnapshotModel.ts).label("max_ts"),
            )
            .where(ConsumerGroupSnapshotModel.cluster_id == cluster_id)
            .group_by(ConsumerGroupSnapshotModel.group_id)
            .subquery()
        )

        # Main query: 최신 스냅샷만 조회
        stmt = (
            select(ConsumerGroupSnapshotModel)
            .join(
                subq,
                (ConsumerGroupSnapshotModel.group_id == subq.c.group_id)
                & (ConsumerGroupSnapshotModel.ts == subq.c.max_ts),
            )
            .where(ConsumerGroupSnapshotModel.cluster_id == cluster_id)
        )

        async with self._session_factory() as session:
            result = await session.execute(stmt)
        snapshots = list(result.scalars().all())

        # 2. ORM Model → Response DTO 변환
        groups = [self._to_response(snapshot) for snapshot in snapshots]

        return ConsumerGroupListResponse(
            groups=groups,
            total=len(groups),
        )

    def _to_response(self, model: ConsumerGroupSnapshotModel) -> ConsumerGroupResponse:
        """ORM Model → Response DTO 변환"""
        return ConsumerGroupResponse(
            cluster_id=model.cluster_id,
            group_id=model.group_id,
            ts=model.ts,
            state=model.state,
            partition_assignor=model.partition_assignor,
            member_count=model.member_count,
            topic_count=model.topic_count,
            lag_stats=LagStatsResponse(
                total_lag=model.total_lag,
                mean_lag=model.total_lag / model.topic_count if model.topic_count > 0 else 0.0,
                p50_lag=model.p50_lag or 0,
                p95_lag=model.p95_lag or 0,
                max_lag=model.max_lag or 0,
                partition_count=model.topic_count,  # Note: 실제로는 파티션 수가 필요
            ),
        )
