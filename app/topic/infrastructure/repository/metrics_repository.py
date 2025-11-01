"""메트릭 스냅샷 Repository"""

from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.topic.domain.models.metrics import TopicMetrics
from app.topic.domain.repositories.interfaces import IMetricsRepository
from app.topic.infrastructure.models.metrics_models import (
    LeaderDistribution,
    MetricsSnapshot,
    TopicPartitionMetrics,
)


class MySQLMetricsRepository(IMetricsRepository):
    """메트릭 스냅샷 MySQL Repository (Session Factory 패턴)"""

    def __init__(
        self, session_factory: Callable[[], AbstractAsyncContextManager[AsyncSession]]
    ) -> None:
        """초기화

        Args:
            session_factory: AsyncSession 생성 팩토리
        """
        self._session_factory = session_factory

    async def save_snapshot(
        self,
        cluster_id: str,
        metrics: TopicMetrics,
        leader_distribution: dict[int, int],
    ) -> int:
        """메트릭 스냅샷 저장

        Args:
            cluster_id: 클러스터 ID
            metrics: 수집된 메트릭 데이터
            leader_distribution: 브로커별 리더 파티션 수

        Returns:
            생성된 스냅샷 ID
        """
        async with self._session_factory() as session:
            # 1. 메인 스냅샷 생성
            snapshot = MetricsSnapshot(
                cluster_id=cluster_id,
                collected_at=datetime.now(UTC),
                broker_count=metrics.cluster_metrics.broker_count,
                total_partitions=metrics.cluster_metrics.total_partition_count,
                partition_to_broker_ratio=metrics.cluster_metrics.partition_to_broker_ratio,
            )
            session.add(snapshot)
            await session.flush()  # ID 생성

            # 2. 토픽별 메트릭 저장
            for topic_name, topic_meta in metrics.topic_meta.items():
                partitions = topic_meta.partition_details
                if not partitions:
                    continue

                total_size = sum(p.partition_size for p in partitions)
                avg_size = int(round(total_size / len(partitions), 0))

                topic_metric = TopicPartitionMetrics(
                    snapshot_id=snapshot.id,
                    topic_name=topic_name,
                    partition_count=len(partitions),
                    total_size_bytes=total_size,
                    avg_partition_size=avg_size,
                    max_partition_size=max(p.partition_size for p in partitions),
                    min_partition_size=min(p.partition_size for p in partitions),
                )
                session.add(topic_metric)

            # 3. 리더 분포 저장
            for broker_id, leader_count in leader_distribution.items():
                leader_dist = LeaderDistribution(
                    snapshot_id=snapshot.id,
                    broker_id=broker_id,
                    leader_partition_count=leader_count,
                )
                session.add(leader_dist)

            await session.commit()
            return snapshot.id

    async def get_latest_snapshot(self, cluster_id: str) -> MetricsSnapshot | None:
        """최신 스냅샷 조회

        Args:
            cluster_id: 클러스터 ID

        Returns:
            최신 스냅샷 (없으면 None)
        """
        async with self._session_factory() as session:
            stmt = (
                select(MetricsSnapshot)
                .where(MetricsSnapshot.cluster_id == cluster_id)
                .order_by(MetricsSnapshot.collected_at.desc())
                .limit(1)
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def get_snapshots_by_timerange(
        self,
        cluster_id: str,
        start_time: datetime,
        end_time: datetime,
    ) -> list[MetricsSnapshot]:
        """시간 범위로 스냅샷 조회

        Args:
            cluster_id: 클러스터 ID
            start_time: 시작 시간
            end_time: 종료 시간

        Returns:
            스냅샷 목록
        """
        async with self._session_factory() as session:
            stmt = (
                select(MetricsSnapshot)
                .where(
                    MetricsSnapshot.cluster_id == cluster_id,
                    MetricsSnapshot.collected_at >= start_time,
                    MetricsSnapshot.collected_at <= end_time,
                )
                .order_by(MetricsSnapshot.collected_at.desc())
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def delete_old_snapshots(self, cluster_id: str, days: int = 7) -> int:
        """오래된 스냅샷 삭제

        Args:
            cluster_id: 클러스터 ID
            days: 보관 기간 (일)

        Returns:
            삭제된 개수
        """
        async with self._session_factory() as session:
            cutoff_date = (datetime.now(UTC) - timedelta(days=days)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )

            stmt = select(MetricsSnapshot).where(
                MetricsSnapshot.cluster_id == cluster_id,
                MetricsSnapshot.collected_at < cutoff_date,
            )
            result = await session.execute(stmt)
            snapshots = result.scalars().all()

            for snapshot in snapshots:
                await session.delete(snapshot)

            await session.commit()
            return len(snapshots)

    async def get_latest_cluster_summary(self, cluster_id: str) -> dict[str, object]:
        """최신 스냅샷 기반 클러스터 요약 조회"""
        async with self._session_factory() as session:
            # 최신 스냅샷 조회
            snapshot_stmt = (
                select(MetricsSnapshot)
                .where(MetricsSnapshot.cluster_id == cluster_id)
                .order_by(MetricsSnapshot.collected_at.desc())
                .limit(1)
            )
            snapshot_result = await session.execute(snapshot_stmt)
            snapshot = snapshot_result.scalar_one_or_none()
            if snapshot is None:
                raise ValueError("No metrics snapshot found for cluster")

            # 리더 분포 조회
            leader_stmt = select(LeaderDistribution).where(
                LeaderDistribution.snapshot_id == snapshot.id
            )
            leader_result = await session.execute(leader_stmt)
            leaders = leader_result.scalars().all()
            leader_distribution = {ld.broker_id: ld.leader_partition_count for ld in leaders}

            return {
                "broker_count": snapshot.broker_count,
                "total_partition_count": snapshot.total_partitions,
                "partition_to_broker_ratio": snapshot.partition_to_broker_ratio,
                "leader_distribution": leader_distribution,
            }

    async def get_latest_topic_distribution(self, cluster_id: str) -> dict[str, object]:
        """최신 스냅샷 기반 전체 토픽 분포 요약 조회"""
        async with self._session_factory() as session:
            # 최신 스냅샷 조회
            snapshot_stmt = (
                select(MetricsSnapshot)
                .where(MetricsSnapshot.cluster_id == cluster_id)
                .order_by(MetricsSnapshot.collected_at.desc())
                .limit(1)
            )
            snapshot_result = await session.execute(snapshot_stmt)
            snapshot = snapshot_result.scalar_one_or_none()
            if snapshot is None:
                raise ValueError("No metrics snapshot found for cluster")

            # 토픽별 메트릭 조회
            metrics_stmt = select(TopicPartitionMetrics).where(
                TopicPartitionMetrics.snapshot_id == snapshot.id
            )
            metrics_result = await session.execute(metrics_stmt)
            rows = list(metrics_result.scalars().all())

            topics: dict[str, dict[str, int]] = {}
            for row in rows:
                topics[row.topic_name] = {
                    "partition_count": row.partition_count,
                    "total_size_bytes": int(row.total_size_bytes),
                    "avg_partition_size": int(row.avg_partition_size),
                }

            return {
                "cluster_info": {
                    "total_topics": len(rows),
                    "total_partitions": snapshot.total_partitions,
                    "total_brokers": snapshot.broker_count,
                    "partition_to_broker_ratio": snapshot.partition_to_broker_ratio,
                },
                "topics": topics,
            }

    async def get_latest_topic_metrics(self, cluster_id: str, topic_name: str) -> dict[str, object]:
        """최신 스냅샷 기반 특정 토픽 메트릭 조회

        Note: 스냅샷에는 파티션 상세(leader/replicas/isr/offset_lag)가 저장되지 않아 partitions는 빈 리스트로 반환합니다.
        """
        async with self._session_factory() as session:
            # 최신 스냅샷 조회
            snapshot_stmt = (
                select(MetricsSnapshot)
                .where(MetricsSnapshot.cluster_id == cluster_id)
                .order_by(MetricsSnapshot.collected_at.desc())
                .limit(1)
            )
            snapshot_result = await session.execute(snapshot_stmt)
            snapshot = snapshot_result.scalar_one_or_none()
            if snapshot is None:
                raise ValueError("No metrics snapshot found for cluster")

            # 해당 토픽 메트릭 조회
            metric_stmt = select(TopicPartitionMetrics).where(
                TopicPartitionMetrics.snapshot_id == snapshot.id,
                TopicPartitionMetrics.topic_name == topic_name,
            )
            metric_result = await session.execute(metric_stmt)
            row = metric_result.scalar_one_or_none()
            if row is None:
                raise ValueError("No metrics found for topic in latest snapshot")

            return {
                "topic_name": topic_name,
                "partition_count": row.partition_count,
                "storage": {
                    "total_size": int(row.total_size_bytes),
                    "max_partition_size": int(row.max_partition_size),
                    "min_partition_size": int(row.min_partition_size),
                    "avg_partition_size": int(row.avg_partition_size),
                },
                "partitions": [],
            }
