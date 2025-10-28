"""Rebalance Domain Models

리밸런스 관련 도메인 모델
- RebalanceDelta: 리밸런스 변경 이벤트
- RebalanceRollup: 시간 윈도우별 집계
- WindowType: 집계 윈도우 타입

참고: cal.md 3️⃣ - Rebalance Churn Score 계산
"""

from dataclasses import dataclass
from datetime import datetime

from app.consumer.domain.types_enum import WindowType


@dataclass(slots=True, kw_only=True)
class RebalanceDelta:
    """리밸런스 델타 도메인 엔티티

    리밸런스 발생 시 변경 내역 (해시 기반 변경 감지)

    책임:
    - 파티션 이동 추적 (moved_partitions)
    - 멤버 증감 추적 (join_count, leave_count)
    - 경과 시간 기록 (elapsed_since_prev_s)
    - 할당 해시 저장 (assignment_hash: SHA-1)

    용도:
    - Rebalance Churn Score 계산 (cal.md 3️⃣)
    - Movement Rate 계산
    - Stable Ratio 계산
    """

    # 식별자
    cluster_id: str
    group_id: str

    # 리밸런스 발생 시각
    ts: datetime

    # 델타 정보
    moved_partitions: int  # 이전 대비 이동한 파티션 수
    join_count: int  # 새로 참여한 멤버 수
    leave_count: int  # 떠난 멤버 수

    # 경과 시간
    elapsed_since_prev_s: int | None  # 직전 리밸런스 이후 경과 시간 (초)

    # 상태
    state: str  # 리밸런스 후 그룹 상태

    # 할당 해시 (변경 감지용)
    assignment_hash: str  # TP→Member 매핑의 SHA-1 해시

    def movement_rate(self, total_partitions: int) -> float:
        """이동률 계산 (cal.md 3️⃣)

        movement_rate = moved_partitions / total_partitions

        Args:
            total_partitions: 전체 파티션 수

        Returns:
            이동률 (0.0 ~ 1.0)
        """
        if total_partitions == 0:
            return 0.0
        return min(1.0, self.moved_partitions / total_partitions)

    def is_significant_movement(self, threshold: float = 0.1) -> bool:
        """의미 있는 이동 여부

        Args:
            threshold: 의미 있는 이동률 임계값 (기본 10%)
        """
        # total_partitions가 필요하므로 외부에서 계산 필요
        # 여기서는 단순히 moved_partitions > 0으로 판단
        return self.moved_partitions > 0

    def has_membership_changes(self) -> bool:
        """멤버 변경 여부 (join 또는 leave)"""
        return self.join_count > 0 or self.leave_count > 0

    def net_member_change(self) -> int:
        """순 멤버 변화 (join - leave)"""
        return self.join_count - self.leave_count

    def __repr__(self) -> str:
        return (
            f"<RebalanceDelta("
            f"group_id={self.group_id}, "
            f"moved={self.moved_partitions}, "
            f"join={self.join_count}, "
            f"leave={self.leave_count}"
            f")>"
        )


@dataclass(slots=True, kw_only=True)
class RebalanceRollup:
    """리밸런스 롤업 도메인 엔티티

    시간 윈도우별 리밸런스 통계 집계 (5분/1시간)

    책임:
    - 리밸런스 횟수 집계 (rebalances)
    - 파티션 이동 통계 (avg_moved_partitions, max_moved_partitions)
    - 안정 유지 비율 (stable_ratio)

    용도:
    - Rebalance Score 계산 (cal.md 3️⃣)
    - 장기 트렌드 분석

    계산 공식 (cal.md 3️⃣):
    - rebalance_score = 100 - alpha * rebalances_per_hour (alpha=10)
    - stable_ratio = stable_time / (stable_time + rebalancing_time)
    """

    # 식별자
    cluster_id: str
    group_id: str

    # 윈도우 정보
    window_start: datetime
    window: WindowType

    # 리밸런스 통계
    rebalances: int  # 윈도우 내 리밸런스 횟수
    avg_moved_partitions: float | None  # 평균 이동 파티션 수
    max_moved_partitions: int | None  # 최대 이동 파티션 수

    # 안정성 지표
    stable_ratio: float | None  # 안정 유지 비율 (0.0 ~ 1.0)

    def rebalances_per_hour(self) -> float:
        """시간당 리밸런스 횟수

        Returns:
            시간당 리밸런스 발생 횟수
        """
        if self.window == WindowType.FIVE_MINUTES:
            # 5분 → 1시간 환산 (12배)
            return self.rebalances * 12
        elif self.window == WindowType.ONE_HOUR:
            return float(self.rebalances)
        return 0.0

    def rebalance_score(self, alpha: float = 10.0) -> float:
        """리밸런스 안정성 점수 (cal.md 3️⃣)

        rebalance_score = 100 - alpha * rebalances_per_hour

        Args:
            alpha: 가중치 (기본 10.0)

        Returns:
            안정성 점수 (0 ~ 100, 높을수록 안정)
        """
        score = 100.0 - alpha * self.rebalances_per_hour()
        return max(0.0, min(100.0, score))  # 0~100 범위로 제한

    def is_stable(self, score_threshold: float = 80.0) -> bool:
        """안정 상태 여부

        Args:
            score_threshold: 안정 판단 점수 임계값 (기본 80)

        Returns:
            True if rebalance_score >= threshold
        """
        return self.rebalance_score() >= score_threshold

    def is_churning(self, score_threshold: float = 50.0) -> bool:
        """과도한 리밸런싱 여부 (Churning)

        Args:
            score_threshold: Churning 판단 점수 임계값 (기본 50)

        Returns:
            True if rebalance_score < threshold
        """
        return self.rebalance_score() < score_threshold

    def stickiness_score(self) -> float:
        """고정성 점수 (cal.md 3️⃣)

        stickiness = 1 - movement_rate

        Note: avg_moved_partitions를 사용하여 근사 계산
        """
        if self.avg_moved_partitions is None or self.avg_moved_partitions == 0:
            return 1.0
        # 간단한 근사: 이동이 적을수록 높은 점수
        return max(0.0, 1.0 - (self.avg_moved_partitions / 100.0))

    def __repr__(self) -> str:
        return (
            f"<RebalanceRollup("
            f"group_id={self.group_id}, "
            f"window={self.window.value}, "
            f"rebalances={self.rebalances}, "
            f"score={self.rebalance_score():.1f}"
            f")>"
        )
