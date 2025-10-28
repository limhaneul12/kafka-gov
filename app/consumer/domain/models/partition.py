"""Consumer Partition Domain Models

파티션별 오프셋 및 Lag 정보
- ConsumerPartition: 파티션 상태
- StuckPartition: 멈춘 파티션 (cal.md 2️⃣)

참고: cal.md 2️⃣ - Stuck Partition 감지 로직
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True, kw_only=True)
class ConsumerPartition:
    """Consumer Partition 도메인 엔티티

    Consumer Group이 소비하는 개별 파티션 정보

    책임:
    - 파티션 식별 (cluster_id, group_id, topic, partition)
    - 오프셋 정보 (committed_offset, latest_offset, lag)
    - 할당 멤버 (assigned_member_id)

    용도:
    - Lag 통계 계산
    - Stuck Partition 감지
    """

    # 식별자
    cluster_id: str
    group_id: str
    topic: str
    partition: int

    # 스냅샷 시각
    ts: datetime

    # 오프셋 정보
    committed_offset: int | None  # 그룹의 커밋 오프셋
    latest_offset: int | None  # 브로커 최신 오프셋
    lag: int | None  # latest_offset - committed_offset

    # 할당 정보
    assigned_member_id: str | None  # 담당 consumer 멤버 ID

    def is_assigned(self) -> bool:
        """멤버에게 할당 여부"""
        return self.assigned_member_id is not None

    def is_lagging(self, threshold: int = 1000) -> bool:
        """Lag 발생 여부

        Args:
            threshold: Lag 임계값 (기본 1000)
        """
        return self.lag is not None and self.lag > threshold

    def has_high_lag(self, threshold: int = 10000) -> bool:
        """높은 Lag 여부

        Args:
            threshold: 높은 Lag 임계값 (기본 10000)
        """
        return self.lag is not None and self.lag > threshold

    def is_caught_up(self, tolerance: int = 10) -> bool:
        """따라잡음 여부 (거의 최신)

        Args:
            tolerance: 허용 오차 (기본 10)
        """
        return self.lag is not None and self.lag <= tolerance

    def __repr__(self) -> str:
        return (
            f"<ConsumerPartition("
            f"topic={self.topic}, "
            f"partition={self.partition}, "
            f"lag={self.lag}, "
            f"member={self.assigned_member_id}"
            f")>"
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class StuckPartition:
    """멈춘 파티션 Value Object

    커밋은 멈췄는데 lag만 증가하는 파티션 (숨은 장애)

    감지 조건 (cal.md 2️⃣):
    - Δcommitted ≤ ε (예: 0 또는 1 이하)
    - AND Δlag > θ (예: 10 이상)
    - AND 지속시간 ≥ T_min (예: 3분)

    출력 예시:
    ```json
    {
      "topic": "orders",
      "partition": 7,
      "member_id": "consumer-3",
      "since_ts": "2025-10-24T16:20:00Z",
      "current_lag": 15234
    }
    ```
    """

    # 식별 정보
    cluster_id: str
    group_id: str
    topic: str
    partition: int

    # 멈춤 감지 정보
    assigned_member_id: str | None  # 담당 멤버
    since_ts: datetime  # 멈춤 시작 시각
    detected_ts: datetime  # 감지 시각

    # Lag 정보
    current_lag: int  # 현재 lag
    delta_committed: int  # Δcommitted (이전 대비 변화)
    delta_lag: int  # Δlag (이전 대비 변화)

    # 임계값 정보 (감지 기준)
    epsilon: int = 1  # Δcommitted 임계값
    theta: int = 10  # Δlag 임계값

    def stuck_duration_seconds(self, now: datetime) -> float:
        """멈춤 지속 시간 (초)

        Args:
            now: 현재 시각

        Returns:
            since_ts부터 현재까지 경과 시간 (초)
        """
        return (now - self.since_ts).total_seconds()

    def is_critical(self, lag_threshold: int = 50000) -> bool:
        """심각한 상태 여부

        Args:
            lag_threshold: 심각한 lag 임계값 (기본 50000)
        """
        return self.current_lag > lag_threshold

    def meets_detection_criteria(self) -> bool:
        """감지 기준 충족 여부

        cal.md 2️⃣ 기준:
        - Δcommitted ≤ ε
        - Δlag > θ
        """
        return self.delta_committed <= self.epsilon and self.delta_lag > self.theta

    def __repr__(self) -> str:
        return (
            f"<StuckPartition("
            f"topic={self.topic}, "
            f"partition={self.partition}, "
            f"lag={self.current_lag}, "
            f"stuck_since={self.since_ts.isoformat()}"
            f")>"
        )
