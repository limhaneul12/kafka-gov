"""Collect Consumer Snapshot Use Case

주기적으로 Consumer Group 데이터 수집 및 저장

책임:
- Kafka AdminClient로부터 데이터 수집
- Domain Service로 계산
- Repository에 저장
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.consumer.domain.services import ConsumerDataCollector
from app.consumer.infrastructure.kafka_consumer_adapter import KafkaConsumerAdapter
from app.consumer.infrastructure.repository import ConsumerRepository


class CollectSnapshotUseCase:
    """Consumer Group 스냅샷 수집 Use Case

    주기적으로 실행되어 Consumer Group 상태를 수집하고 DB에 저장

    사용 예시:
    ```python
    use_case = CollectSnapshotUseCase(session)
    await use_case.execute(cluster_id, group_id, adapter)
    ```
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Args:
            session: Database Session
        """
        self._session = session
        self._repo = ConsumerRepository(session)

    async def execute(self, cluster_id: str, group_id: str, adapter: KafkaConsumerAdapter) -> None:
        """Consumer Group 스냅샷 수집 및 저장

        Args:
            cluster_id: 클러스터 ID
            group_id: Consumer Group ID
            adapter: Kafka AdminClient Adapter

        Raises:
            KeyError: 그룹이 존재하지 않음
            Exception: Kafka 연결 오류 또는 DB 오류
        """
        # 1. 데이터 수집
        collector = ConsumerDataCollector(adapter, cluster_id)

        group = await collector.collect_group(group_id)
        members = await collector.collect_members(group_id)
        partitions = await collector.collect_partitions(group_id)

        # 2. DB 저장
        await self._repo.save_full_snapshot(group, members, partitions)

        # 3. Stuck Partition 감지 (선택적)
        # TODO: 이전 스냅샷과 비교하여 Stuck Partition 감지 및 저장

        # 4. Commit
        await self._repo.commit()

    async def execute_batch(
        self, cluster_id: str, group_ids: list[str], adapter: KafkaConsumerAdapter
    ) -> dict[str, str]:
        """여러 Consumer Group 배치 수집

        Args:
            cluster_id: 클러스터 ID
            group_ids: Consumer Group ID 목록
            adapter: Kafka AdminClient Adapter

        Returns:
            결과 맵 {group_id: "success" | "error"}
        """
        results: dict[str, str] = {}

        for group_id in group_ids:
            try:
                await self.execute(cluster_id, group_id, adapter)
                results[group_id] = "success"
            except Exception as e:
                results[group_id] = f"error: {e!s}"
                await self._repo.rollback()

        return results
