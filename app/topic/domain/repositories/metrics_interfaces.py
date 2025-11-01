"""메트릭 리포지토리 인터페이스"""

from abc import ABC, abstractmethod

from ..models.metrics import TopicMetrics


class IPartitionMetricsRepository(ABC):
    """파티션 수 관련 메트릭 리포지토리"""

    @abstractmethod
    async def topic_partition_count(self, topic_name: str) -> int:
        """토픽의 파티션 수"""
        ...

    @abstractmethod
    async def get_total_partition_count(self) -> int:
        """전체 파티션 수"""
        ...


class IStorageMetricsRepository(ABC):
    """저장용량 관련 메트릭 리포지토리"""

    @abstractmethod
    async def topic_partition_size(self, topic_name: str) -> int:
        """토픽의 전체 파티션 크기"""
        ...

    @abstractmethod
    async def topic_max_partition_size(self, topic_name: str) -> int:
        """토픽의 가장 큰 파티션 크기"""
        ...

    @abstractmethod
    async def topic_min_partition_size(self, topic_name: str) -> int:
        """토픽의 가장 작은 파티션 크기"""
        ...

    @abstractmethod
    async def topic_avg_partition_size(self, topic_name: str) -> int:
        """토픽의 평균 파티션 크기"""
        ...


class IClusterMetricsRepository(ABC):
    """클러스터 및 브로커 관련 메트릭 리포지토리"""

    @abstractmethod
    async def get_cluster_broker_count(self) -> int:
        """클러스터 브로커 수"""
        ...

    @abstractmethod
    async def get_partition_to_broker_ratio(self) -> float:
        """파티션 수 대비 브로커 수 비율"""
        ...

    @abstractmethod
    async def get_total_partition_count(self) -> int:
        """전체 파티션 수"""
        ...


class ILeaderDistributionRepository(ABC):
    """리더 분포 관련 메트릭 리포지토리"""

    @abstractmethod
    async def get_leader_distribution(self) -> dict[int, int]:
        """리더 분포 (브로커별 리더 파티션 수)"""
        ...


class IMetricsRepository(ABC):
    """통합 메트릭 리포지토리"""

    @abstractmethod
    async def get_all_topic_metrics(self) -> TopicMetrics | None:
        """전체 토픽 메트릭 조회"""
        ...

    @abstractmethod
    async def refresh(self) -> None:
        """스냅샷 강제 갱신"""
        ...
