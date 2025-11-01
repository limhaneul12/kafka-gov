"""메트릭 도메인 모델"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PartitionDetails:
    """파티션 상세 정보"""

    partition_index: int
    partition_size: int
    offset_lag: int
    is_future_key: bool

    # 복제 정보
    leader: int  # Leader broker ID
    replicas: list[int]  # 복제본이 있는 broker ID 목록
    isr: list[int]  # In-Sync Replicas broker ID 목록


@dataclass(frozen=True, slots=True)
class TopicMeta:
    """토픽 메타데이터"""

    partition_details: list[PartitionDetails]


@dataclass(frozen=True, slots=True)
class ClusterMetrics:
    """클러스터 전체 지표"""

    broker_count: int
    total_partition_count: int
    topics: dict[str, TopicMeta]

    @property
    def partition_to_broker_ratio(self) -> float:
        """파티션 대 브로커 비율 계산"""
        if self.broker_count == 0:
            return 0.0
        return self.total_partition_count / self.broker_count


@dataclass(frozen=True, slots=True)
class TopicMetrics:
    """토픽 단위 지표"""

    log_dir: str
    topic_meta: dict[str, TopicMeta]
    cluster_metrics: ClusterMetrics
