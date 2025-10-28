"""Consumer Query Use Cases

Consumer Group 조회 관련 Use Case들을 통합

"""

import logging
from collections.abc import Awaitable, Callable
from contextlib import AbstractAsyncContextManager
from datetime import timedelta

from confluent_kafka.admin import AdminClient
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.consumer.domain.models import ConsumerPartition, RebalanceRollup
from app.consumer.domain.services import (
    ConsumerDataCollector,
    ConsumerMetricsCalculator,
    StuckPartitionDetector,
)
from app.consumer.domain.thresholds import DEFAULT_THRESHOLDS
from app.consumer.domain.types_enum import WindowType
from app.consumer.infrastructure.kafka_consumer_adapter import KafkaConsumerAdapter
from app.consumer.infrastructure.models import (
    ConsumerGroupRebalanceDeltaModel,
    ConsumerPartitionSnapshotModel,
)
from app.consumer.infrastructure.repository import ConsumerRepository
from app.consumer.interface.schema import (
    ConsumerGroupListResponse,
    ConsumerGroupResponse,
    LagStatsResponse,
)
from app.consumer.interface.schema.detail_schema import (
    ConsumerGroupSummaryResponse,
    MemberDetailResponse,
    PartitionDetailResponse,
    RebalanceEventResponse,
    TopicConsumerMappingResponse,
)


class ListConsumerGroupsUseCase:
    """Consumer Group 목록 조회 Use Case - 실시간 Kafka 조회"""

    def __init__(self, admin_client_getter: Callable[[str], Awaitable[AdminClient]]) -> None:
        """Use case 생성자

        Args:
            admin_client_getter: cluster_id로 AdminClient를 가져오는 async 함수
        """
        self._admin_client_getter = admin_client_getter

    async def execute(self, cluster_id: str) -> ConsumerGroupListResponse:
        """Consumer Group 목록 조회 - 실시간 Kafka 조회

        Args:
            cluster_id: 클러스터 ID

        Returns:
            ConsumerGroupListResponse

        Raises:
            ValueError: AdminClient를 찾을 수 없음
        """
        # 1. AdminClient 및 Adapter 생성
        admin_client = await self._admin_client_getter(cluster_id)

        adapter = KafkaConsumerAdapter(admin_client)
        collector = ConsumerDataCollector(adapter, cluster_id)

        # 2. 모든 Consumer Group 목록 조회
        try:
            group_infos = await adapter.list_consumer_groups()
            all_groups = [
                await collector.collect_group(group_info.group_id) for group_info in group_infos
            ]
        except Exception:
            # 조회 실패 시 빈 리스트 반환
            return ConsumerGroupListResponse(groups=[], total=0)

        # 3. Response DTO 변환
        groups = [
            ConsumerGroupResponse(
                cluster_id=group.cluster_id,
                group_id=group.group_id,
                ts=group.ts,
                state=group.state.value,
                partition_assignor=group.partition_assignor.value
                if group.partition_assignor
                else None,
                member_count=group.member_count,
                topic_count=group.topic_count,
                lag_stats=LagStatsResponse(
                    total_lag=group.lag_stats.total_lag,
                    mean_lag=group.lag_stats.mean_lag,
                    p50_lag=group.lag_stats.p50_lag,
                    p95_lag=group.lag_stats.p95_lag,
                    max_lag=group.lag_stats.max_lag,
                    partition_count=group.topic_count,
                ),
            )
            for group in all_groups
        ]

        return ConsumerGroupListResponse(
            groups=groups,
            total=len(groups),
        )


class GetConsumerGroupSummaryUseCase:
    """Consumer Group Summary Use Case - 실시간 Kafka 조회 방식"""

    def __init__(
        self,
        admin_client_getter: Callable[[str], Awaitable[AdminClient]],
        session_factory: Callable[[], AbstractAsyncContextManager[AsyncSession]] | None = None,
    ) -> None:
        """Use case 생성자

        Args:
            admin_client_getter: cluster_id로 AdminClient를 가져오는 async 함수
            session_factory: Delta 조회용 세션 팩토리 (optional)
        """
        self._admin_client_getter = admin_client_getter
        self._session_factory = session_factory
        self._calculator = ConsumerMetricsCalculator()

    async def execute(self, cluster_id: str, group_id: str) -> ConsumerGroupSummaryResponse:
        """그룹 Summary 생성 - 실시간 Kafka 조회

        Args:
            cluster_id: 클러스터 ID
            group_id: Consumer Group ID

        Raises:
            ValueError: AdminClient를 찾을 수 없거나 그룹이 존재하지 않음
        """
        # 1. AdminClient 및 Adapter 생성
        admin_client = await self._admin_client_getter(cluster_id)

        adapter = KafkaConsumerAdapter(admin_client)
        collector = ConsumerDataCollector(adapter, cluster_id)

        # 2. 실시간 Kafka 조회
        try:
            group = await collector.collect_group(group_id)
            members = await collector.collect_members(group_id)
            partitions = await collector.collect_partitions(group_id)
        except KeyError as e:
            raise ValueError(f"Consumer group not found: {group_id}") from e

        # 3. 공정성(Gini) 계산 - 실시간 데이터로
        fairness = self._calculator.calculate_fairness(members, partitions)

        # 4. 리밸런스 점수 및 Stuck 파티션 (Delta 조회, optional)
        # 기본값: None (데이터 없으면 "알 수 없음")
        rebalance_score: float | None = None
        stuck_partitions: list[dict[str, object]] = []
        if self._session_factory is not None:
            async with self._session_factory() as session:
                repo = ConsumerRepository(session)

                rollup_model = await repo.get_latest_rollup(
                    cluster_id, group_id, WindowType.ONE_HOUR
                )
                if rollup_model is not None:
                    rollup = RebalanceRollup(
                        cluster_id=rollup_model.cluster_id,
                        group_id=rollup_model.group_id,
                        window_start=rollup_model.window_start,
                        window=WindowType(rollup_model.window),
                        rebalances=rollup_model.rebalances,
                        avg_moved_partitions=rollup_model.avg_moved_partitions,
                        max_moved_partitions=rollup_model.max_moved_partitions,
                        stable_ratio=rollup_model.stable_ratio,
                    )
                    rebalance_score = rollup.rebalance_score()

                stuck_partitions = await self._get_stuck_partitions(
                    session, repo, cluster_id, group_id
                )

        # 5. Summary 응답 조립 - 실시간 데이터 사용
        return ConsumerGroupSummaryResponse(
            group_id=group_id,
            cluster_id=cluster_id,
            state=group.state.value,
            member_count=group.member_count,
            topic_count=len({p.topic for p in partitions}),
            lag={
                "p50": group.lag_stats.p50_lag,
                "p95": group.lag_stats.p95_lag,
                "max": group.lag_stats.max_lag,
                "total": group.lag_stats.total_lag,
            },
            rebalance_score=rebalance_score,
            fairness_gini=fairness.gini_coefficient,
            stuck=stuck_partitions,
        )

    async def _get_stuck_partitions(
        self,
        session: AsyncSession,
        repo: ConsumerRepository,
        cluster_id: str,
        group_id: str,
    ) -> list[dict[str, object]]:
        """DB 스냅샷을 활용한 Stuck Partition 감지"""
        latest_snapshot = await repo.get_latest_group_snapshot(cluster_id, group_id)
        if latest_snapshot is None:
            return []

        current_models = await repo.get_partition_snapshots(
            cluster_id=cluster_id, group_id=group_id, ts=latest_snapshot.ts
        )
        if not current_models:
            return []

        thresholds = DEFAULT_THRESHOLDS.stuck
        threshold_ts = latest_snapshot.ts - timedelta(seconds=thresholds.duration_s_ge)

        previous_subquery = (
            select(
                ConsumerPartitionSnapshotModel.topic.label("topic"),
                ConsumerPartitionSnapshotModel.partition.label("partition"),
                func.max(ConsumerPartitionSnapshotModel.ts).label("ts"),
            )
            .where(
                ConsumerPartitionSnapshotModel.cluster_id == cluster_id,
                ConsumerPartitionSnapshotModel.group_id == group_id,
                ConsumerPartitionSnapshotModel.ts <= threshold_ts,
            )
            .group_by(
                ConsumerPartitionSnapshotModel.topic,
                ConsumerPartitionSnapshotModel.partition,
            )
            .subquery()
        )

        previous_result = await session.execute(
            select(ConsumerPartitionSnapshotModel).join(
                previous_subquery,
                (
                    (ConsumerPartitionSnapshotModel.topic == previous_subquery.c.topic)
                    & (ConsumerPartitionSnapshotModel.partition == previous_subquery.c.partition)
                    & (ConsumerPartitionSnapshotModel.ts == previous_subquery.c.ts)
                ),
            )
        )
        previous_models = list(previous_result.scalars().all())
        if not previous_models:
            return []

        current_partitions = [self._snapshot_to_partition(model) for model in current_models]
        previous_partitions = [self._snapshot_to_partition(model) for model in previous_models]

        detector = StuckPartitionDetector(
            epsilon=thresholds.delta_committed_le,
            theta=thresholds.delta_lag_ge,
            min_duration_seconds=thresholds.duration_s_ge,
        )

        previous_map = {
            (p.cluster_id, p.group_id, p.topic, p.partition): p for p in previous_partitions
        }

        stuck: list[dict[str, object]] = []
        for current in current_partitions:
            key = (current.cluster_id, current.group_id, current.topic, current.partition)
            previous = previous_map.get(key)
            if previous is None:
                continue

            if current.ts - previous.ts < timedelta(seconds=thresholds.duration_s_ge):
                continue

            if not detector.is_stuck(current, previous):
                continue

            stuck_partition = detector.create_stuck_partition(current, previous, previous.ts)
            stuck.append(
                {
                    "topic": stuck_partition.topic,
                    "partition": stuck_partition.partition,
                    "assigned_member_id": stuck_partition.assigned_member_id,
                    "since_ts": stuck_partition.since_ts,
                    "current_lag": stuck_partition.current_lag,
                    "delta_committed": stuck_partition.delta_committed,
                    "delta_lag": stuck_partition.delta_lag,
                }
            )

        stuck.sort(key=lambda item: item["current_lag"], reverse=True)
        return stuck

    @staticmethod
    def _snapshot_to_partition(model: ConsumerPartitionSnapshotModel) -> ConsumerPartition:
        """ORM 스냅샷 모델 → Domain ConsumerPartition 변환"""
        return ConsumerPartition(
            cluster_id=model.cluster_id,
            group_id=model.group_id,
            topic=model.topic,
            partition=model.partition,
            ts=model.ts,
            committed_offset=model.committed_offset,
            latest_offset=model.latest_offset,
            lag=model.lag,
            assigned_member_id=model.assigned_member_id,
        )


class GetGroupMembersUseCase:
    """Consumer Group 멤버 목록 Use Case - 실시간 Kafka 조회"""

    def __init__(self, admin_client_getter: Callable[[str], Awaitable[AdminClient]]) -> None:
        """Use case 생성자

        Args:
            admin_client_getter: cluster_id로 AdminClient를 가져오는 함수
        """
        self._admin_client_getter = admin_client_getter

    async def execute(self, cluster_id: str, group_id: str) -> list[MemberDetailResponse]:
        """멤버 목록 조회 - 실시간 Kafka 조회

        Args:
            cluster_id: 클러스터 ID
            group_id: Consumer Group ID

        Returns:
            멤버 상세 목록

        Raises:
            ValueError: AdminClient를 찾을 수 없거나 그룹이 존재하지 않음
        """
        # 1. AdminClient 및 Adapter 생성
        admin_client = await self._admin_client_getter(cluster_id)

        adapter = KafkaConsumerAdapter(admin_client)
        collector = ConsumerDataCollector(adapter, cluster_id)

        # 2. 실시간 Kafka 조회
        try:
            members = await collector.collect_members(group_id)
            partitions = await collector.collect_partitions(group_id)
        except KeyError:
            # 그룹이 없으면 빈 리스트 반환
            return []

        # 3. 멤버별 파티션 매핑
        partitions_by_member: dict[str, list[dict[str, int | str]]] = {}
        for p in partitions:
            if p.assigned_member_id:
                partitions_by_member.setdefault(p.assigned_member_id, []).append(
                    {"topic": p.topic, "partition": p.partition}
                )

        # 4. 응답 조립
        return [
            MemberDetailResponse(
                member_id=m.member_id,
                client_id=m.client_id,
                client_host=m.client_host,
                assigned_partitions=partitions_by_member.get(m.member_id, []),
            )
            for m in members
        ]


class GetGroupPartitionsUseCase:
    """Consumer Group 파티션 목록 Use Case - 실시간 Kafka 조회"""

    def __init__(self, admin_client_getter: Callable[[str], Awaitable[AdminClient]]) -> None:
        """Use case 생성자

        Args:
            admin_client_getter: cluster_id로 AdminClient를 가져오는 함수
        """
        self._admin_client_getter = admin_client_getter

    async def execute(self, cluster_id: str, group_id: str) -> list[PartitionDetailResponse]:
        """파티션 목록 조회 - 실시간 Kafka 조회

        Args:
            cluster_id: 클러스터 ID
            group_id: Consumer Group ID

        Returns:
            파티션 상세 목록

        Raises:
            ValueError: AdminClient를 찾을 수 없거나 그룹이 존재하지 않음
        """
        # 1. AdminClient 및 Adapter 생성
        admin_client = await self._admin_client_getter(cluster_id)

        adapter = KafkaConsumerAdapter(admin_client)
        collector = ConsumerDataCollector(adapter, cluster_id)

        # 2. 실시간 Kafka 조회
        try:
            partitions = await collector.collect_partitions(group_id)
        except KeyError:
            # 그룹이 없으면 빈 리스트 반환
            return []

        # 3. 응답 조립
        return [
            PartitionDetailResponse(
                topic=p.topic,
                partition=p.partition,
                committed_offset=p.committed_offset,
                latest_offset=p.latest_offset,
                lag=p.lag,
                assigned_member_id=p.assigned_member_id,
            )
            for p in partitions
        ]


class GetGroupRebalanceUseCase:
    """Consumer Group 리밸런스 이벤트 Use Case"""

    def __init__(
        self, session_factory: Callable[[], AbstractAsyncContextManager[AsyncSession]]
    ) -> None:
        self._session_factory = session_factory

    async def execute(
        self, cluster_id: str, group_id: str, limit: int = 10
    ) -> list[RebalanceEventResponse]:
        async with self._session_factory() as session:
            stmt = (
                select(ConsumerGroupRebalanceDeltaModel)
                .where(
                    ConsumerGroupRebalanceDeltaModel.cluster_id == cluster_id,
                    ConsumerGroupRebalanceDeltaModel.group_id == group_id,
                )
                .order_by(desc(ConsumerGroupRebalanceDeltaModel.ts))
                .limit(limit)
            )
            result = await session.execute(stmt)
            delta_models = list(result.scalars().all())

        return [
            RebalanceEventResponse(
                ts=d.ts,
                moved_partitions=d.moved_partitions,
                join_count=d.join_count,
                leave_count=d.leave_count,
                elapsed_since_prev_s=d.elapsed_since_prev_s,
                state=d.state,
            )
            for d in delta_models
        ]


class GetTopicConsumersUseCase:
    """토픽별 컨슈머 매핑 Use Case - 실시간 Kafka 조회"""

    def __init__(self, admin_client_getter: Callable[[str], Awaitable[AdminClient]]) -> None:
        """Use case 생성자

        Args:
            admin_client_getter: cluster_id로 AdminClient를 가져오는 함수
        """
        self._admin_client_getter = admin_client_getter

    async def execute(self, cluster_id: str, topic: str) -> TopicConsumerMappingResponse:
        """토픽별 컨슈머 매핑 조회 - 실시간 Kafka 조회

        Args:
            cluster_id: 클러스터 ID
            topic: 토픽 이름

        Returns:
            TopicConsumerMappingResponse

        Raises:
            ValueError: AdminClient를 찾을 수 없음
        """
        # 1. AdminClient 및 Adapter 생성
        admin_client = await self._admin_client_getter(cluster_id)

        adapter = KafkaConsumerAdapter(admin_client)
        collector = ConsumerDataCollector(adapter, cluster_id)

        # 2. 모든 Consumer Group 목록 조회
        try:
            group_infos = await adapter.list_consumer_groups()
            all_groups = [
                await collector.collect_group(group_info.group_id) for group_info in group_infos
            ]

        except Exception as e:
            # 조회 실패 시 에러 로깅 후 빈 리스트 반환
            logging.error(f"Failed to collect consumer groups for topic {topic}: {e}")
            return TopicConsumerMappingResponse(topic=topic, consumer_groups=[])

        # 3. 해당 토픽을 구독하는 그룹 필터링
        consumer_groups: list[dict] = []

        logging.warning(
            f"🔍 [Topic Filter] Filtering topic '{topic}' from {len(all_groups)} consumer groups"
        )

        for group in all_groups:
            try:
                # 각 그룹의 파티션 조회
                partitions = await collector.collect_partitions(group.group_id)
                logging.warning(
                    f"📊 [Group Partitions] Group '{group.group_id}' has {len(partitions)} partitions: "
                    f"{[(p.topic, p.partition) for p in partitions]}"
                )

                # 해당 토픽의 파티션만 필터링
                topic_partitions = [p for p in partitions if p.topic == topic]

                if topic_partitions:
                    logging.warning(
                        f"✅ [Match Found] Group '{group.group_id}' consumes topic '{topic}' "
                        f"({len(topic_partitions)} partitions)"
                    )

                    # Frontend가 필요로 하는 모든 필드 포함
                    consumer_groups.append(
                        {
                            "group_id": group.group_id,
                            "state": group.state.value,
                            "member_count": group.member_count,
                            # Frontend가 기대하는 추가 필드들 (기본값 설정)
                            "slo_compliance": getattr(group, "slo_compliance", 0.0),
                            "lag_p50": getattr(group, "lag_p50", 0),
                            "lag_p95": getattr(group, "lag_p95", 0),
                            "lag_max": max((p.lag for p in topic_partitions), default=0),
                            "stuck_count": getattr(group, "stuck_count", 0),
                            "rebalance_score": getattr(group, "rebalance_score", 0.0),
                            "fairness_gini": getattr(group, "fairness_gini", 0.0),
                            "recommendation": getattr(group, "recommendation", None),
                            "partitions": [
                                {
                                    "partition": p.partition,
                                    "assigned_member_id": p.assigned_member_id,
                                    "lag": p.lag,
                                }
                                for p in topic_partitions
                            ],
                        }
                    )
            except Exception as e:
                # 개별 그룹 조회 실패 시 로깅하고 건너뜀
                logging.warning(f"Failed to collect partitions for group {group.group_id}: {e}")
                continue

        return TopicConsumerMappingResponse(
            topic=topic,
            consumer_groups=consumer_groups,
        )
