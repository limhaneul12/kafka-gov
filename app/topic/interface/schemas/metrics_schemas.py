"""메트릭 스키마"""

from pydantic import BaseModel, Field


class StorageMetrics(BaseModel):
    """저장용량 메트릭"""

    total_size: int = Field(..., description="전체 파티션 크기 (바이트)")
    max_partition_size: int = Field(..., description="최대 파티션 크기 (바이트)")
    min_partition_size: int = Field(..., description="최소 파티션 크기 (바이트)")
    avg_partition_size: int = Field(..., description="평균 파티션 크기 (바이트)")


class PartitionDetail(BaseModel):
    """파티션 상세 정보"""

    partition: int = Field(..., description="파티션 번호")
    size: int = Field(..., description="파티션 크기 (바이트)")
    leader: int = Field(..., description="Leader broker ID")
    replicas: list[int] = Field(..., description="복제본이 있는 broker ID 목록")
    isr: list[int] = Field(..., description="In-Sync Replicas broker ID 목록")
    offset_lag: int = Field(..., description="복제 지연 (offset)")


class TopicMetricsResponse(BaseModel):
    """토픽 메트릭 응답"""

    topic_name: str = Field(..., description="토픽 이름")
    partition_count: int = Field(..., description="파티션 수")
    storage: StorageMetrics = Field(..., description="저장용량 메트릭")
    partitions: list[PartitionDetail] = Field(..., description="각 파티션 상세 정보")


class ClusterInfoMetrics(BaseModel):
    """클러스터 정보 메트릭"""

    total_topics: int = Field(..., description="전체 토픽 수")
    total_partitions: int = Field(..., description="전체 파티션 수")
    total_brokers: int = Field(..., description="전체 브로커 수")
    partition_to_broker_ratio: float = Field(..., description="파티션/브로커 비율")


class TopicSummary(BaseModel):
    """토픽 요약 정보"""

    partition_count: int = Field(..., description="파티션 수")
    total_size_bytes: int = Field(..., description="전체 크기 (바이트)")
    avg_partition_size: int = Field(..., description="평균 파티션 크기 (바이트)")


class TopicDistributionResponse(BaseModel):
    """토픽 분포 응답"""

    cluster_info: ClusterInfoMetrics = Field(..., description="클러스터 정보")
    topics: dict[str, TopicSummary] = Field(..., description="토픽별 요약")


class ClusterMetricsResponse(BaseModel):
    """클러스터 메트릭 응답"""

    broker_count: int = Field(..., description="브로커 수")
    total_partition_count: int = Field(..., description="전체 파티션 수")
    partition_to_broker_ratio: float = Field(..., description="파티션/브로커 비율")
    leader_distribution: dict[int, int] = Field(..., description="브로커별 리더 파티션 수")
