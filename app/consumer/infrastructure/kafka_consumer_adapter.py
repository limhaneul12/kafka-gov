"""Kafka Consumer AdminClient Adapter

Confluent Kafka AdminClient를 사용한 Consumer Group 데이터 수집

주요 API:
- list_consumer_groups() → 전체 그룹 목록
- describe_consumer_groups() → 그룹 상세 (state, members, assignor)
- list_consumer_group_offsets() → 커밋 오프셋
- list_offsets() → 최신 오프셋 (OffsetSpec.latest())

비동기 처리:
- AdminClient는 동기 API + Future 반환
- asyncio.to_thread()로 Future.result() 호출을 스레드풀에서 실행
- 외부 API는 완전 비동기 (async/await)

참고:
- job.md: Consumer Governance 요구사항
- Confluent Kafka Python Docs: https://docs.confluent.io/platform/current/clients/confluent-kafka-python/html/index.html
"""

import asyncio
from collections.abc import Sequence

from confluent_kafka import (
    ConsumerGroupState,
    ConsumerGroupTopicPartitions,
    TopicPartition as KafkaTopicPartition,
)
from confluent_kafka.admin import AdminClient, OffsetSpec

from app.consumer.domain.value_objects import (
    BrokerInfo,
    ConsumerGroupDescription,
    ConsumerGroupInfo,
    MemberInfo,
    PartitionOffset,
    TopicPartition,
)
from app.shared.logging_config import get_logger

logger = get_logger(__name__)


class KafkaConsumerAdapter:
    """Kafka Consumer AdminClient Adapter

    Consumer Group 정보를 Confluent Kafka AdminClient로 수집

    사용 예시:
    ```python
    adapter = KafkaConsumerAdapter(admin_client)

    # 전체 그룹 목록
    groups = await adapter.list_consumer_groups()

    # 그룹 상세
    desc = await adapter.describe_consumer_group("my-group")

    # 커밋 오프셋
    offsets = await adapter.get_committed_offsets("my-group")

    # 최신 오프셋
    latest = await adapter.get_latest_offsets([("orders", 0), ("orders", 1)])
    ```
    """

    def __init__(self, admin_client: AdminClient) -> None:
        """
        Args:
            admin_client: Confluent Kafka AdminClient 인스턴스
        """
        self._admin = admin_client

    async def list_consumer_groups(self) -> list[ConsumerGroupInfo]:
        """전체 Consumer Group 목록 조회

        AdminClient API: list_consumer_groups(request_timeout, states, types)
        → Future[ListConsumerGroupsResult]

        ConsumerGroupListing 속성:
        - group_id: str
        - is_simple_consumer_group: bool
        - state: ConsumerGroupState
        - type: ConsumerGroupType

        Returns:
            Consumer Group 목록

        Raises:
            Exception: Kafka 연결 오류
        """
        # 1. Future 생성 (빠름, non-blocking)
        future = self._admin.list_consumer_groups(request_timeout=30.0)

        # 2. Future.result() 호출을 스레드풀에서 실행
        result = await asyncio.to_thread(future.result)

        return [
            ConsumerGroupInfo(
                group_id=group.group_id,
                state=self._map_state(group.state),
                is_simple_consumer_group=group.is_simple_consumer_group,
                group_type=str(group.type),  # ConsumerGroupType enum → str
            )
            for group in result.valid
        ]

    async def describe_consumer_group(self, group_id: str) -> ConsumerGroupDescription:
        """Consumer Group 상세 정보 조회

        AdminClient API: describe_consumer_groups(group_ids, include_authorized_operations, request_timeout)
        → dict[str, Future[ConsumerGroupDescription]]

        Args:
            group_id: Consumer Group ID

        Returns:
            그룹 상세 정보 (state, members, assignor)

        Raises:
            KeyError: 그룹이 존재하지 않음
            Exception: Kafka 연결 오류
        """
        # 1. Future 딕셔너리 생성 (빠름)
        futures = self._admin.describe_consumer_groups([group_id], request_timeout=30.0)

        # 2. 해당 그룹의 Future 가져오기
        if group_id not in futures:
            raise KeyError(f"Consumer group not found: {group_id}")

        future = futures[group_id]

        # 3. Future.result() 호출을 스레드풀에서 실행
        try:
            desc = await asyncio.to_thread(future.result)
        except Exception as e:
            # Empty/Dead 그룹이거나 권한 없음
            raise KeyError(f"Consumer group not found: {group_id}") from e

        # 4. 멤버 정보 변환
        members: list[MemberInfo] = [
            MemberInfo(
                member_id=member.member_id,
                client_id=member.client_id,
                client_host=member.host,
                assignments=[
                    TopicPartition(topic=tp.topic, partition=tp.partition)
                    for tp in member.assignment.topic_partitions
                ]
                if member.assignment
                else [],
            )
            for member in desc.members
        ]

        return ConsumerGroupDescription(
            group_id=desc.group_id,
            state=self._map_state(desc.state),
            partition_assignor=desc.partition_assignor or "unknown",
            members=members,
            coordinator=BrokerInfo(
                broker_id=desc.coordinator.id,
                host=desc.coordinator.host,
                port=desc.coordinator.port,
            ),
        )

    async def get_committed_offsets(
        self, group_id: str, partitions: list[TopicPartition] | None = None
    ) -> list[PartitionOffset]:
        """Consumer Group의 커밋 오프셋 조회

        AdminClient API: list_consumer_group_offsets(
            list_consumer_group_offsets_request: list[ConsumerGroupTopicPartitions],
            require_stable: bool,
            request_timeout: float
        ) → dict[str, Future[ConsumerGroupTopicPartitions]]

        Args:
            group_id: Consumer Group ID
            partitions: 조회할 파티션 목록 (None이면 전체)

        Returns:
            파티션별 커밋 오프셋

        Raises:
            Exception: Kafka 연결 오류
        """
        # 1. ConsumerGroupTopicPartitions 생성
        kafka_partitions: list[KafkaTopicPartition] | None = None
        if partitions:
            kafka_partitions = [KafkaTopicPartition(tp.topic, tp.partition) for tp in partitions]

        # ConsumerGroupTopicPartitions 객체 생성
        # - group_id: Consumer Group ID
        # - topic_partitions: 조회할 파티션 목록 (None이면 전체)
        request = ConsumerGroupTopicPartitions(group_id=group_id, topic_partitions=kafka_partitions)

        # 2. Future 딕셔너리 생성
        futures = self._admin.list_consumer_group_offsets(
            [request], require_stable=False, request_timeout=30.0
        )

        # 3. 해당 그룹의 Future 가져오기
        if group_id not in futures:
            return []

        future = futures[group_id]

        # 4. Future.result() 호출을 스레드풀에서 실행
        try:
            result = await asyncio.to_thread(future.result)
        except Exception as e:
            # 그룹이 없거나 오프셋 정보 없음
            logger.warning(
                "consumer_group_offset_not_found",
                group_id=group_id,
                error_type=e.__class__.__name__,
            )
            return []

        # 5. ConsumerGroupTopicPartitions → PartitionOffset 변환
        # Kafka는 커밋되지 않은 오프셋을 -1001로 반환 → None으로 변환
        return [
            PartitionOffset(
                topic=tp.topic,
                partition=tp.partition,
                offset=tp.offset if tp.offset >= 0 else None,  # -1001 → None
            )
            for tp in result.topic_partitions
        ]

    async def get_latest_offsets(
        self, partitions: Sequence[tuple[str, int]]
    ) -> list[PartitionOffset]:
        """파티션의 최신 오프셋 조회 (브로커의 끝)

        AdminClient API: list_offsets(
            topic_partition_offsets: dict[TopicPartition, OffsetSpec],
            isolation_level: IsolationLevel,
            request_timeout: float
        ) → dict[TopicPartition, Future[ListOffsetsResultInfo]]

        Args:
            partitions: (topic, partition) 튜플 목록

        Returns:
            파티션별 최신 오프셋

        Raises:
            Exception: Kafka 연결 오류
        """
        # 1. OffsetSpec 매핑 생성
        offset_spec_map = {
            KafkaTopicPartition(topic, partition): OffsetSpec.latest()
            for topic, partition in partitions
        }

        # 2. Future 딕셔너리 생성 (빠름)
        futures = self._admin.list_offsets(offset_spec_map, request_timeout=30.0)

        # 3. 모든 Future를 병렬로 대기
        async def _get_offset(tp: KafkaTopicPartition, future) -> PartitionOffset | None:
            """단일 파티션 오프셋 조회"""
            try:
                result_info = await asyncio.to_thread(future.result)
                return PartitionOffset(
                    topic=tp.topic, partition=tp.partition, offset=result_info.offset
                )
            except Exception:
                # 파티션 정보 없음
                return None

        # 모든 파티션 병렬 조회
        tasks = [_get_offset(tp, future) for tp, future in futures.items()]
        offsets = await asyncio.gather(*tasks)

        # None 제외하고 반환
        return [offset for offset in offsets if offset is not None]

    def _map_state(self, state: ConsumerGroupState) -> str:
        """ConsumerGroupState → 문자열 변환

        Args:
            state: Kafka ConsumerGroupState enum

        Returns:
            "Stable" | "Rebalancing" | "Empty" | "Dead" | "Unknown"
        """
        state_map = {
            ConsumerGroupState.STABLE: "Stable",
            ConsumerGroupState.PREPARING_REBALANCING: "Rebalancing",
            ConsumerGroupState.COMPLETING_REBALANCING: "Rebalancing",
            ConsumerGroupState.EMPTY: "Empty",
            ConsumerGroupState.DEAD: "Dead",
        }
        return state_map.get(state, "Unknown")
