"""Consumer Data Collector Service

Kafka AdminClient Adapter → Domain Model 변환 서비스

책임:
- Consumer Group 정보 수집
- Offset 정보 수집 및 Lag 계산
- Infrastructure DTO → Domain Entity 변환

참고: job.md 3️⃣ - 데이터 수집 항목
"""

import logging
from datetime import UTC, datetime

from app.consumer.domain.models import ConsumerGroup, ConsumerMember, ConsumerPartition, LagStats
from app.consumer.domain.types_enum import GroupState, PartitionAssignor
from app.consumer.domain.value_objects import ConsumerGroupDescription, TopicPartition
from app.consumer.infrastructure.kafka_consumer_adapter import KafkaConsumerAdapter

logger = logging.getLogger(__name__)


class ConsumerDataCollector:
    """Consumer Group 데이터 수집 서비스

    Kafka AdminClient로부터 데이터를 수집하여 Domain 모델로 변환

    사용 예시:
    ```python
    collector = ConsumerDataCollector(adapter)

    # Consumer Group 수집
    group = await collector.collect_group("my-group")

    # Members 수집
    members = await collector.collect_members("my-group")

    # Partitions + Lag 수집
    partitions = await collector.collect_partitions("my-group")
    ```
    """

    def __init__(self, adapter: KafkaConsumerAdapter, cluster_id: str) -> None:
        """
        Args:
            adapter: Kafka AdminClient Adapter
            cluster_id: 클러스터 ID
        """
        self._adapter = adapter
        self._cluster_id = cluster_id

    async def collect_group(self, group_id: str) -> ConsumerGroup:
        """Consumer Group 전체 정보 수집

        수집 항목:
        - Group 상태 (state, assignor)
        - 멤버/토픽 카운트
        - Lag 통계 (total, p50, p95, max)

        Args:
            group_id: Consumer Group ID

        Returns:
            ConsumerGroup Domain Entity

        Raises:
            KeyError: 그룹이 존재하지 않음
        """
        # 1. 그룹 상세 조회
        desc = await self._adapter.describe_consumer_group(group_id)

        # 2. 파티션 정보 수집 (Lag 계산 포함)
        partitions = await self.collect_partitions(group_id, desc)

        # 3. Lag 통계 계산
        lag_stats = self._calculate_lag_stats(partitions)

        # 4. 토픽 수 계산
        topics = {p.topic for p in partitions}

        return ConsumerGroup(
            cluster_id=self._cluster_id,
            group_id=group_id,
            ts=datetime.now(UTC),
            state=self._map_group_state(desc.state),
            partition_assignor=self._map_assignor(desc.partition_assignor),
            member_count=len(desc.members),
            topic_count=len(topics),
            lag_stats=lag_stats,
        )

    async def collect_members(
        self, group_id: str, desc: ConsumerGroupDescription | None = None
    ) -> list[ConsumerMember]:
        """Consumer Member 목록 수집

        Args:
            group_id: Consumer Group ID
            desc: ConsumerGroupDescription (없으면 조회)

        Returns:
            ConsumerMember 목록
        """
        if desc is None:
            desc = await self._adapter.describe_consumer_group(group_id)

        ts = datetime.now(UTC)

        return [
            ConsumerMember(
                cluster_id=self._cluster_id,
                group_id=group_id,
                member_id=member_info.member_id,
                ts=ts,
                client_id=member_info.client_id,
                client_host=member_info.client_host,
                assigned_tp_count=len(member_info.assignments),
            )
            for member_info in desc.members
        ]

    async def collect_partitions(
        self, group_id: str, desc: ConsumerGroupDescription | None = None
    ) -> list[ConsumerPartition]:
        """Consumer Partition 목록 수집 (Lag 계산 포함)

        수집 항목:
        - 커밋 오프셋 (list_consumer_group_offsets)
        - 최신 오프셋 (list_offsets)
        - Lag 계산 (latest - committed)
        - 할당 멤버 정보

        Args:
            group_id: Consumer Group ID
            desc: ConsumerGroupDescription (없으면 조회)

        Returns:
            ConsumerPartition 목록
        """
        if desc is None:
            desc = await self._adapter.describe_consumer_group(group_id)

        # 1. 멤버별 할당 파티션 매핑 생성
        assignment_map: dict[tuple[str, int], str] = {}
        all_partitions: list[TopicPartition] = []

        for member in desc.members:
            for tp in member.assignments:
                assignment_map[(tp.topic, tp.partition)] = member.member_id
                all_partitions.append(tp)

        if not all_partitions:
            return []

        # 2. 커밋 오프셋 조회
        committed_offsets = await self._adapter.get_committed_offsets(group_id, all_partitions)
        committed_map = {(o.topic, o.partition): o.offset for o in committed_offsets}

        # 3. 최신 오프셋 조회
        partition_tuples = [(tp.topic, tp.partition) for tp in all_partitions]
        latest_offsets = await self._adapter.get_latest_offsets(partition_tuples)
        latest_map = {(o.topic, o.partition): o.offset for o in latest_offsets}

        # 4. ConsumerPartition 생성
        ts = datetime.now(UTC)
        partitions: list[ConsumerPartition] = []

        for tp in all_partitions:
            key = (tp.topic, tp.partition)
            committed = committed_map.get(key)
            latest = latest_map.get(key)

            # Lag 계산
            lag = None
            if committed is not None and latest is not None:
                calculated_lag = latest - committed

                # 음수 Lag 방어: 토픽 삭제/재생성, retention 등으로 인해 발생 가능
                if calculated_lag < 0:
                    logger.warning(
                        f"Negative lag detected: group={group_id}, topic={tp.topic}, "
                        f"partition={tp.partition}, committed={committed}, latest={latest}, "
                        f"lag={calculated_lag} (상황: 토픽 삭제/재생성 또는 retention 정책)"
                    )

                # Kafka 공식 도구들도 음수 Lag를 0으로 표시
                lag = max(0, calculated_lag)

            partitions.append(
                ConsumerPartition(
                    cluster_id=self._cluster_id,
                    group_id=group_id,
                    topic=tp.topic,
                    partition=tp.partition,
                    ts=ts,
                    committed_offset=committed,
                    latest_offset=latest,
                    lag=lag,
                    assigned_member_id=assignment_map.get(key),
                )
            )

        return partitions

    def _calculate_lag_stats(self, partitions: list[ConsumerPartition]) -> LagStats:
        """Lag 통계 계산 (cal.md 1️⃣)

        계산 항목:
        - total_lag = Σ(lag_i)
        - mean_lag = total_lag / N
        - p50_lag = median({ lag_i })
        - p95_lag = percentile({ lag_i }, 95)
        - max_lag = max({ lag_i })

        Args:
            partitions: ConsumerPartition 목록

        Returns:
            LagStats Value Object
        """
        lags = [p.lag for p in partitions if p.lag is not None]

        if not lags:
            # Lag 정보 없음 (모든 파티션이 커밋되지 않음)
            return LagStats(
                total_lag=0,
                mean_lag=0.0,
                p50_lag=0,
                p95_lag=0,
                max_lag=0,
                partition_count=len(partitions),
            )

        lags_sorted = sorted(lags)
        total_lag = sum(lags)
        mean_lag = total_lag / len(lags)

        # Percentile 계산
        def percentile(data: list[int], p: float) -> int:
            """백분위수 계산 (linear interpolation)"""
            if not data:
                return 0
            k = (len(data) - 1) * p
            f = int(k)
            c = int(k) + 1
            if c >= len(data):
                return data[-1]
            d0 = data[f] * (c - k)
            d1 = data[c] * (k - f)
            return int(d0 + d1)

        p50_lag = percentile(lags_sorted, 0.5)
        p95_lag = percentile(lags_sorted, 0.95)
        max_lag = max(lags)

        return LagStats(
            total_lag=total_lag,
            mean_lag=mean_lag,
            p50_lag=p50_lag,
            p95_lag=p95_lag,
            max_lag=max_lag,
            partition_count=len(partitions),
        )

    def _map_group_state(self, state: str) -> GroupState:
        """Infrastructure state → Domain GroupState 변환"""
        state_map = {
            "Stable": GroupState.STABLE,
            "Rebalancing": GroupState.REBALANCING,
            "Empty": GroupState.EMPTY,
            "Dead": GroupState.DEAD,
        }
        return state_map.get(state, GroupState.EMPTY)

    def _map_assignor(self, assignor: str) -> PartitionAssignor | None:
        """Assignor 문자열 → Domain PartitionAssignor 변환

        Kafka에서 사용하는 Assignor 이름:
        - range, RangeAssignor
        - roundrobin, RoundRobinAssignor
        - sticky, StickyAssignor
        - cooperative-sticky, CooperativeStickyAssignor
        """
        assignor_lower = assignor.lower()

        if "range" in assignor_lower:
            return PartitionAssignor.RANGE
        if "roundrobin" in assignor_lower:
            return PartitionAssignor.ROUNDROBIN
        if "cooperative" in assignor_lower and "sticky" in assignor_lower:
            return PartitionAssignor.COOPERATIVE_STICKY
        if "sticky" in assignor_lower:
            return PartitionAssignor.STICKY

        return None
