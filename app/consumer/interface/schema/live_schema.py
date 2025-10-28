"""Consumer Group Live Monitoring Schema

실시간 모니터링용 경량 스키마
"""

from datetime import datetime

from pydantic import BaseModel, Field


class PartitionLiveInfo(BaseModel):
    """파티션 실시간 정보 (경량)"""

    topic: str
    partition: int
    lag: int | None
    committed_offset: int | None
    latest_offset: int | None
    assigned_member_id: str | None


class MemberLiveInfo(BaseModel):
    """멤버 실시간 정보 (경량)"""

    member_id: str
    client_id: str
    partition_count: int


class LagStatsLive(BaseModel):
    """Lag 통계 (실시간)"""

    total_lag: int
    mean_lag: float
    p50_lag: int
    p95_lag: int
    max_lag: int
    partition_count: int


class ConsumerGroupLiveSnapshot(BaseModel):
    """Consumer Group 실시간 스냅샷

    10초마다 갱신되는 실시간 모니터링 데이터
    단일 타임스탬프로 데이터 일관성 보장
    """

    # 메타 정보
    timestamp: datetime = Field(..., description="스냅샷 수집 시간 (일관성 보장)")
    cluster_id: str
    group_id: str

    # 그룹 상태
    state: str = Field(..., description="Stable, Rebalancing, Dead, Empty")
    member_count: int
    topic_count: int
    partition_assignor: str | None

    # Lag 통계
    lag_stats: LagStatsLive

    # 파티션 상세 (Lag 포함)
    partitions: list[PartitionLiveInfo] = Field(
        default_factory=list, description="파티션별 Lag 정보"
    )

    # 멤버 정보
    members: list[MemberLiveInfo] = Field(default_factory=list, description="멤버 할당 정보")

    # 거버넌스 지표
    fairness_gini: float = Field(..., description="Gini 계수 (0=완벽, 1=불균형)")
    stuck_count: int = Field(0, description="Stuck 파티션 수")

    # 이벤트 플래그
    is_rebalancing: bool = Field(False, description="리밸런싱 진행 중")
    has_lag_spike: bool = Field(False, description="Lag 급증 감지")


class LiveStreamEvent(BaseModel):
    """실시간 스트림 이벤트"""

    type: str = Field(..., description="snapshot, alert, heartbeat")
    data: ConsumerGroupLiveSnapshot | dict | None
    message: str | None = None
