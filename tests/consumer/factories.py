"""Consumer 테스트용 Factory 함수"""

from datetime import datetime, timezone

from app.consumer.domain.models.group import ConsumerGroup, LagStats
from app.consumer.domain.types_enum import GroupState, PartitionAssignor


def create_consumer_group(
    *,
    cluster_id: str = "test-cluster",
    group_id: str = "test-group",
    ts: datetime | None = None,
    state: str | GroupState = "Stable",
    partition_assignor: str | PartitionAssignor | None = "range",
    member_count: int = 3,
    topic_count: int = 2,
    total_lag: int = 1500,
    p50_lag: int = 450,
    p95_lag: int = 800,
    max_lag: int = 1000,
) -> ConsumerGroup:
    """ConsumerGroup 도메인 객체 생성 팩토리

    Args:
        cluster_id: 클러스터 ID
        group_id: Consumer Group ID
        ts: 타임스탬프 (None이면 현재 시각)
        state: 그룹 상태
        partition_assignor: 파티션 할당 알고리즘
        member_count: 멤버 수
        topic_count: 토픽 수
        total_lag: 전체 lag 합
        p50_lag: P50 lag
        p95_lag: P95 lag
        max_lag: 최대 lag

    Returns:
        ConsumerGroup 도메인 객체
    """
    if ts is None:
        ts = datetime.now(timezone.utc)

    # GroupState Enum 변환
    if isinstance(state, str):
        state = GroupState(state)

    # PartitionAssignor Enum 변환
    if isinstance(partition_assignor, str):
        partition_assignor = PartitionAssignor(partition_assignor)

    # LagStats 생성
    partition_count = topic_count * 2  # 간단한 추정
    mean_lag = total_lag / partition_count if partition_count > 0 else 0.0

    lag_stats = LagStats(
        total_lag=total_lag,
        mean_lag=mean_lag,
        p50_lag=p50_lag,
        p95_lag=p95_lag,
        max_lag=max_lag,
        partition_count=partition_count,
    )

    return ConsumerGroup(
        cluster_id=cluster_id,
        group_id=group_id,
        ts=ts,
        state=state,
        partition_assignor=partition_assignor,
        member_count=member_count,
        topic_count=topic_count,
        lag_stats=lag_stats,
    )
