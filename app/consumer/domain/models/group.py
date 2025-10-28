"""Consumer Group Domain Models

Consumer Group의 핵심 도메인 모델 정의
- ConsumerGroup: 그룹 전체 상태
- GroupState: 그룹 상태 Enum
- LagStats: Lag 통계 (cal.md 1️⃣)

참고: cal.md - Lag 통계 계산 공식
"""

from dataclasses import dataclass
from datetime import datetime

from app.consumer.domain.types_enum import GroupState, PartitionAssignor


@dataclass(frozen=True, slots=True, kw_only=True)
class LagStats:
    """Lag 통계 Value Object

    Consumer Group의 전체 Lag 분포 통계

    계산 공식 (cal.md 1️⃣):
    - total_lag = Σ(lag_i)
    - mean_lag = total_lag / N (N = 파티션 수)
    - p50_lag = median({ lag_i })
    - p95_lag = percentile({ lag_i }, 95)
    - max_lag = max({ lag_i })

    용도:
    - 그룹의 소비 지연 진단
    - SLO 준수율 계산 기준
    """

    total_lag: int  # 전체 lag 합
    mean_lag: float  # 평균 lag
    p50_lag: int  # P50 (중간값)
    p95_lag: int  # P95 (95% 구간)
    max_lag: int  # 최대 lag
    partition_count: int  # 파티션 수 (계산 검증용)

    def is_healthy(self, threshold_p95: int = 10000) -> bool:
        """건강 상태 판단

        Args:
            threshold_p95: P95 lag 임계값 (기본 10000)

        Returns:
            True if healthy (p95_lag <= threshold)
        """
        return self.p95_lag <= threshold_p95

    def slo_compliance_rate(self, target_p95_ms: int) -> float:
        """SLO 준수율 계산 (cal.md 5️⃣)

        Args:
            target_p95_ms: 목표 P95 lag (밀리초)

        Returns:
            준수율 (0.0 ~ 1.0)
        """
        if self.p95_lag <= target_p95_ms:
            return 1.0
        # 초과 비율 계산 (간단 모델)
        return max(0.0, 1.0 - (self.p95_lag - target_p95_ms) / target_p95_ms)


@dataclass(slots=True, kw_only=True)
class ConsumerGroup:
    """Consumer Group 도메인 엔티티

    Consumer Group의 전체 상태를 나타내는 집합근(Aggregate Root)

    책임:
    - 그룹 식별 정보 (cluster_id, group_id)
    - 상태 정보 (state, assignor)
    - 멤버/토픽 카운트
    - Lag 통계
    - 스냅샷 시각
    """

    # 식별자
    cluster_id: str
    group_id: str

    # 스냅샷 시각
    ts: datetime

    # 상태 정보
    state: GroupState
    partition_assignor: PartitionAssignor | None

    # 카운트 정보
    member_count: int
    topic_count: int

    # Lag 통계
    lag_stats: LagStats

    def is_stable(self) -> bool:
        """안정 상태 여부"""
        return self.state == GroupState.STABLE

    def is_rebalancing(self) -> bool:
        """리밸런싱 중 여부"""
        return self.state == GroupState.REBALANCING

    def is_empty(self) -> bool:
        """빈 그룹 여부 (멤버 없음)"""
        return self.state == GroupState.EMPTY or self.member_count == 0

    def has_high_lag(self, threshold: int = 100000) -> bool:
        """높은 Lag 여부

        Args:
            threshold: Total lag 임계값 (기본 100000)
        """
        return self.lag_stats.total_lag > threshold

    def needs_attention(self, p95_threshold: int = 10000) -> bool:
        """주의 필요 여부

        다음 조건 중 하나라도 만족하면 주의 필요:
        - 리밸런싱 중
        - P95 lag이 임계값 초과
        - 멤버가 없음 (Empty)
        """
        return (
            self.is_rebalancing() or not self.lag_stats.is_healthy(p95_threshold) or self.is_empty()
        )

    def __repr__(self) -> str:
        return (
            f"<ConsumerGroup("
            f"group_id={self.group_id}, "
            f"state={self.state.value}, "
            f"members={self.member_count}, "
            f"total_lag={self.lag_stats.total_lag}"
            f")>"
        )
