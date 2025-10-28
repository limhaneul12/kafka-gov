"""Consumer Repository - Database Access Layer

Domain Models → ORM Models 변환 및 CRUD

책임:
- 스냅샷 저장 (Group, Member, Partition)
- 리밸런스 이벤트 저장 (Delta, Rollup)
- 시계열 데이터 조회
- ORM ↔ Domain 매퍼

참고: job.md - DB 구조
"""

from datetime import datetime

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.consumer.domain.models import (
    ConsumerGroup,
    ConsumerMember,
    ConsumerPartition,
    RebalanceDelta,
    RebalanceRollup,
)
from app.consumer.domain.types_enum import WindowType
from app.consumer.infrastructure.models import (
    ConsumerGroupRebalanceDeltaModel,
    ConsumerGroupRebalanceRollupModel,
    ConsumerGroupSnapshotModel,
    ConsumerMemberSnapshotModel,
    ConsumerPartitionSnapshotModel,
)


class ConsumerRepository:
    """Consumer 데이터 Repository

    Domain Service에서 수집한 데이터를 DB에 저장하고 조회

    사용 예시:
    ```python
    repo = ConsumerRepository(session)

    # 스냅샷 저장
    await repo.save_group_snapshot(group)
    await repo.save_member_snapshots(members)
    await repo.save_partition_snapshots(partitions)

    # 조회
    latest = await repo.get_latest_group_snapshot(cluster_id, group_id)
    history = await repo.get_group_snapshot_history(cluster_id, group_id, hours=24)
    ```
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Args:
            session: SQLAlchemy AsyncSession
        """
        self._session = session

    # ========================================================================
    # Group Snapshot
    # ========================================================================

    async def save_group_snapshot(self, group: ConsumerGroup) -> ConsumerGroupSnapshotModel:
        """Consumer Group 스냅샷 저장

        Args:
            group: ConsumerGroup Domain Entity

        Returns:
            저장된 ORM Model
        """
        model = ConsumerGroupSnapshotModel(
            cluster_id=group.cluster_id,
            group_id=group.group_id,
            ts=group.ts,
            state=group.state.value,
            partition_assignor=group.partition_assignor.value if group.partition_assignor else None,
            member_count=group.member_count,
            topic_count=group.topic_count,
            total_lag=group.lag_stats.total_lag,
            p50_lag=group.lag_stats.p50_lag,
            p95_lag=group.lag_stats.p95_lag,
            max_lag=group.lag_stats.max_lag,
        )

        self._session.add(model)
        await self._session.flush()

        return model

    async def get_latest_group_snapshot(
        self, cluster_id: str, group_id: str
    ) -> ConsumerGroupSnapshotModel | None:
        """최신 Group 스냅샷 조회

        Args:
            cluster_id: 클러스터 ID
            group_id: Consumer Group ID

        Returns:
            최신 스냅샷 ORM Model or None
        """
        stmt = (
            select(ConsumerGroupSnapshotModel)
            .where(
                ConsumerGroupSnapshotModel.cluster_id == cluster_id,
                ConsumerGroupSnapshotModel.group_id == group_id,
            )
            .order_by(desc(ConsumerGroupSnapshotModel.ts))
            .limit(1)
        )

        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_group_snapshot_history(
        self, cluster_id: str, group_id: str, hours: int = 24
    ) -> list[ConsumerGroupSnapshotModel]:
        """Group 스냅샷 히스토리 조회

        Args:
            cluster_id: 클러스터 ID
            group_id: Consumer Group ID
            hours: 조회 시간 (기본 24시간)

        Returns:
            스냅샷 목록 (시간 역순)
        """
        from datetime import timedelta

        cutoff_time = datetime.now() - timedelta(hours=hours)

        stmt = (
            select(ConsumerGroupSnapshotModel)
            .where(
                ConsumerGroupSnapshotModel.cluster_id == cluster_id,
                ConsumerGroupSnapshotModel.group_id == group_id,
                ConsumerGroupSnapshotModel.ts >= cutoff_time,
            )
            .order_by(desc(ConsumerGroupSnapshotModel.ts))
        )

        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    # ========================================================================
    # Member Snapshot
    # ========================================================================

    async def save_member_snapshots(
        self, members: list[ConsumerMember]
    ) -> list[ConsumerMemberSnapshotModel]:
        """Consumer Member 스냅샷 배치 저장

        Args:
            members: ConsumerMember 목록

        Returns:
            저장된 ORM Model 목록
        """
        models = [
            ConsumerMemberSnapshotModel(
                cluster_id=member.cluster_id,
                group_id=member.group_id,
                ts=member.ts,
                member_id=member.member_id,
                client_id=member.client_id,
                client_host=member.client_host,
                assigned_tp_count=member.assigned_tp_count,
            )
            for member in members
        ]

        self._session.add_all(models)
        await self._session.flush()

        return models

    # ========================================================================
    # Partition Snapshot
    # ========================================================================

    async def save_partition_snapshots(
        self, partitions: list[ConsumerPartition]
    ) -> list[ConsumerPartitionSnapshotModel]:
        """Consumer Partition 스냅샷 배치 저장

        Args:
            partitions: ConsumerPartition 목록

        Returns:
            저장된 ORM Model 목록
        """
        models = [
            ConsumerPartitionSnapshotModel(
                cluster_id=partition.cluster_id,
                group_id=partition.group_id,
                ts=partition.ts,
                topic=partition.topic,
                partition=partition.partition,
                committed_offset=partition.committed_offset,
                latest_offset=partition.latest_offset,
                lag=partition.lag,
                assigned_member_id=partition.assigned_member_id,
            )
            for partition in partitions
        ]

        self._session.add_all(models)
        await self._session.flush()

        return models

    async def get_partition_snapshots(
        self, cluster_id: str, group_id: str, ts: datetime | None = None
    ) -> list[ConsumerPartitionSnapshotModel]:
        """특정 시각의 Partition 스냅샷 조회

        Args:
            cluster_id: 클러스터 ID
            group_id: Consumer Group ID
            ts: 조회 시각 (None이면 최신)

        Returns:
            파티션 스냅샷 목록
        """
        if ts is None:
            # 최신 스냅샷 조회
            latest_snapshot = await self.get_latest_group_snapshot(cluster_id, group_id)
            if latest_snapshot is None:
                return []
            ts = latest_snapshot.ts

        stmt = select(ConsumerPartitionSnapshotModel).where(
            ConsumerPartitionSnapshotModel.cluster_id == cluster_id,
            ConsumerPartitionSnapshotModel.group_id == group_id,
            ConsumerPartitionSnapshotModel.ts == ts,
        )

        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    # ========================================================================
    # Rebalance Delta
    # ========================================================================

    async def save_rebalance_delta(self, delta: RebalanceDelta) -> ConsumerGroupRebalanceDeltaModel:
        """리밸런스 델타 저장

        Args:
            delta: RebalanceDelta Domain Entity

        Returns:
            저장된 ORM Model
        """
        model = ConsumerGroupRebalanceDeltaModel(
            cluster_id=delta.cluster_id,
            group_id=delta.group_id,
            ts=delta.ts,
            moved_partitions=delta.moved_partitions,
            join_count=delta.join_count,
            leave_count=delta.leave_count,
            elapsed_since_prev_s=delta.elapsed_since_prev_s,
            state=delta.state,
            assignment_hash=delta.assignment_hash,
        )

        self._session.add(model)
        await self._session.flush()

        return model

    # ========================================================================
    # Rebalance Rollup
    # ========================================================================

    async def save_rebalance_rollup(
        self, rollup: RebalanceRollup
    ) -> ConsumerGroupRebalanceRollupModel:
        """리밸런스 롤업 저장

        Args:
            rollup: RebalanceRollup Domain Entity

        Returns:
            저장된 ORM Model
        """
        model = ConsumerGroupRebalanceRollupModel(
            cluster_id=rollup.cluster_id,
            group_id=rollup.group_id,
            window_start=rollup.window_start,
            window=rollup.window.value,
            rebalances=rollup.rebalances,
            avg_moved_partitions=rollup.avg_moved_partitions,
            max_moved_partitions=rollup.max_moved_partitions,
            stable_ratio=rollup.stable_ratio,
        )

        self._session.add(model)
        await self._session.flush()

        return model

    async def get_latest_rollup(
        self, cluster_id: str, group_id: str, window: WindowType
    ) -> ConsumerGroupRebalanceRollupModel | None:
        """최신 리밸런스 롤업 조회

        Args:
            cluster_id: 클러스터 ID
            group_id: Consumer Group ID
            window: 윈도우 타입 (5m/1h)

        Returns:
            최신 롤업 ORM Model or None
        """
        stmt = (
            select(ConsumerGroupRebalanceRollupModel)
            .where(
                ConsumerGroupRebalanceRollupModel.cluster_id == cluster_id,
                ConsumerGroupRebalanceRollupModel.group_id == group_id,
                ConsumerGroupRebalanceRollupModel.window == window.value,
            )
            .order_by(desc(ConsumerGroupRebalanceRollupModel.window_start))
            .limit(1)
        )

        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    # ========================================================================
    # Batch Operations
    # ========================================================================

    async def save_full_snapshot(
        self,
        group: ConsumerGroup,
        members: list[ConsumerMember],
        partitions: list[ConsumerPartition],
    ) -> None:
        """전체 스냅샷 배치 저장 (트랜잭션)

        Args:
            group: ConsumerGroup
            members: ConsumerMember 목록
            partitions: ConsumerPartition 목록
        """
        await self.save_group_snapshot(group)
        await self.save_member_snapshots(members)
        await self.save_partition_snapshots(partitions)

        # flush는 각 메서드에서 이미 호출됨
        # commit은 외부(Use Case)에서 수행

    async def commit(self) -> None:
        """트랜잭션 커밋"""
        await self._session.commit()

    async def rollback(self) -> None:
        """트랜잭션 롤백"""
        await self._session.rollback()
