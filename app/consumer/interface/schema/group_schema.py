"""Consumer Group Response Schemas

API Response용 Pydantic 스키마
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class LagStatsResponse(BaseModel):
    """Lag 통계 응답"""

    model_config = ConfigDict(
        frozen=True,
        json_schema_extra={
            "example": {
                "total_lag": 15234,
                "mean_lag": 507.8,
                "p50_lag": 450,
                "p95_lag": 1200,
                "max_lag": 2500,
                "partition_count": 30,
            }
        },
    )

    total_lag: int = Field(description="전체 lag 합")
    mean_lag: float = Field(description="평균 lag")
    p50_lag: int = Field(description="P50 lag (중간값)")
    p95_lag: int = Field(description="P95 lag")
    max_lag: int = Field(description="최대 lag")
    partition_count: int = Field(description="파티션 수")


class ConsumerGroupResponse(BaseModel):
    """Consumer Group 응답"""

    model_config = ConfigDict(
        frozen=True,
        json_schema_extra={
            "example": {
                "cluster_id": "prod-cluster-01",
                "group_id": "order-processor",
                "ts": "2025-10-27T23:45:00Z",
                "state": "Stable",
                "partition_assignor": "cooperative-sticky",
                "member_count": 5,
                "topic_count": 3,
                "lag_stats": {
                    "total_lag": 15234,
                    "mean_lag": 507.8,
                    "p50_lag": 450,
                    "p95_lag": 1200,
                    "max_lag": 2500,
                    "partition_count": 30,
                },
            }
        },
    )

    cluster_id: str = Field(description="클러스터 ID")
    group_id: str = Field(description="Consumer Group ID")
    ts: datetime = Field(description="수집 시각")
    state: str = Field(description="그룹 상태 (Stable/Rebalancing/Empty/Dead)")
    partition_assignor: str | None = Field(None, description="파티션 할당 알고리즘")
    member_count: int = Field(description="멤버 수")
    topic_count: int = Field(description="구독 토픽 수")
    lag_stats: LagStatsResponse = Field(description="Lag 통계")


class ConsumerGroupListResponse(BaseModel):
    """Consumer Group 목록 응답"""

    model_config = ConfigDict(
        frozen=True,
        json_schema_extra={
            "example": {
                "groups": [
                    {
                        "cluster_id": "prod-cluster-01",
                        "group_id": "order-processor",
                        "ts": "2025-10-27T23:45:00Z",
                        "state": "Stable",
                        "partition_assignor": "cooperative-sticky",
                        "member_count": 5,
                        "topic_count": 3,
                        "lag_stats": {
                            "total_lag": 15234,
                            "mean_lag": 507.8,
                            "p50_lag": 450,
                            "p95_lag": 1200,
                            "max_lag": 2500,
                            "partition_count": 30,
                        },
                    }
                ],
                "total": 1,
            }
        },
    )

    groups: list[ConsumerGroupResponse] = Field(description="Consumer Group 목록")
    total: int = Field(description="전체 그룹 수")


class ConsumerMemberResponse(BaseModel):
    """Consumer Member 응답"""

    model_config = ConfigDict(frozen=True)

    member_id: str = Field(description="멤버 ID")
    client_id: str | None = Field(None, description="클라이언트 ID")
    client_host: str | None = Field(None, description="호스트 IP")
    assigned_tp_count: int = Field(description="할당된 파티션 수")


class ConsumerPartitionResponse(BaseModel):
    """Consumer Partition 응답"""

    model_config = ConfigDict(frozen=True)

    topic: str = Field(description="토픽 이름")
    partition: int = Field(description="파티션 번호")
    committed_offset: int | None = Field(None, description="커밋 오프셋")
    latest_offset: int | None = Field(None, description="최신 오프셋")
    lag: int | None = Field(None, description="Lag")
    assigned_member_id: str | None = Field(None, description="담당 멤버 ID")


class StuckPartitionResponse(BaseModel):
    """멈춘 파티션 응답"""

    model_config = ConfigDict(frozen=True)

    topic: str = Field(description="토픽 이름")
    partition: int = Field(description="파티션 번호")
    assigned_member_id: str | None = Field(None, description="담당 멤버 ID")
    since_ts: datetime = Field(description="멈춤 시작 시각")
    current_lag: int = Field(description="현재 lag")
    delta_committed: int = Field(description="커밋 변화량")
    delta_lag: int = Field(description="Lag 변화량")


class ConsumerGroupDetailResponse(BaseModel):
    """Consumer Group 상세 응답"""

    model_config = ConfigDict(frozen=True)

    group: ConsumerGroupResponse = Field(description="그룹 정보")
    members: list[ConsumerMemberResponse] = Field(description="멤버 목록")
    partitions: list[ConsumerPartitionResponse] = Field(description="파티션 목록")
    stuck_partitions: list[StuckPartitionResponse] = Field(
        default_factory=list, description="멈춘 파티션 목록"
    )
