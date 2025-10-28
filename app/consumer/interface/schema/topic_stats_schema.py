"""Consumer Group Topic Statistics Schema

토픽별 집계 통계 응답 스키마
"""

from pydantic import BaseModel, Field


class TopicStatsResponse(BaseModel):
    """토픽별 통계 응답"""

    topic: str = Field(..., description="토픽 이름")
    partition_count: int = Field(..., description="파티션 수")
    total_lag: int = Field(..., description="총 lag")
    avg_lag: float = Field(..., description="평균 lag")
    max_lag: int = Field(..., description="최대 lag")
    lag_share: float = Field(..., description="전체 lag 대비 비율 (0.0 ~ 1.0)")


class GroupTopicStatsResponse(BaseModel):
    """그룹 토픽 통계 전체 응답"""

    group_id: str
    cluster_id: str
    total_lag: int = Field(..., description="전체 lag 합계")
    topic_stats: list[TopicStatsResponse] = Field(
        default_factory=list, description="토픽별 통계 (lag 내림차순)"
    )
