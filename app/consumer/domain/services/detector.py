"""Stuck Partition Detector Service

멈춘 파티션 감지 (cal.md 2️⃣)

감지 조건:
- Δcommitted ≤ ε (예: 0 또는 1 이하)
- AND Δlag > θ (예: 10 이상)
- AND 지속시간 ≥ T_min (예: 3분)

참고: cal.md 2️⃣ - Stuck Partition 감지 로직
"""

from datetime import datetime

from app.consumer.domain.models import ConsumerPartition, StuckPartition


class StuckPartitionDetector:
    """Stuck Partition 감지 서비스

    커밋은 멈췄는데 lag만 증가하는 파티션 감지 (숨은 장애)

    사용 예시:
    ```python
    detector = StuckPartitionDetector()

    # 단일 파티션 감지
    if detector.is_stuck(current, previous):
        stuck = detector.create_stuck_partition(current, previous, since_ts)

    # 배치 감지
    stuck_list = detector.detect_stuck_partitions(current_snapshot, previous_snapshot)
    ```
    """

    def __init__(
        self,
        epsilon: int = 1,
        theta: int = 10,
        min_duration_seconds: int = 180,
    ) -> None:
        """
        Args:
            epsilon: Δcommitted 임계값 (기본 1)
            theta: Δlag 임계값 (기본 10)
            min_duration_seconds: 최소 지속 시간 (기본 180초 = 3분)
        """
        self._epsilon = epsilon
        self._theta = theta
        self._min_duration = min_duration_seconds

    def is_stuck(self, current: ConsumerPartition, previous: ConsumerPartition | None) -> bool:
        """파티션이 stuck 상태인지 판단 (cal.md 2️⃣)

        감지 조건:
        1. Δcommitted ≤ ε
        2. Δlag > θ

        Args:
            current: 현재 파티션 상태
            previous: 이전 파티션 상태 (None이면 False)

        Returns:
            True if stuck
        """
        if previous is None:
            return False

        # 동일 파티션인지 확인
        if (
            current.cluster_id != previous.cluster_id
            or current.group_id != previous.group_id
            or current.topic != previous.topic
            or current.partition != previous.partition
        ):
            return False

        # 오프셋/Lag 정보 확인
        if (
            current.committed_offset is None
            or previous.committed_offset is None
            or current.lag is None
            or previous.lag is None
        ):
            return False

        # Δcommitted 계산
        delta_committed = current.committed_offset - previous.committed_offset

        # Δlag 계산
        delta_lag = current.lag - previous.lag

        # 감지 조건 체크
        return delta_committed <= self._epsilon and delta_lag > self._theta

    def create_stuck_partition(
        self,
        current: ConsumerPartition,
        previous: ConsumerPartition,
        since_ts: datetime,
    ) -> StuckPartition:
        """StuckPartition Value Object 생성

        Args:
            current: 현재 파티션 상태
            previous: 이전 파티션 상태
            since_ts: Stuck 시작 시각

        Returns:
            StuckPartition
        """
        delta_committed = (current.committed_offset or 0) - (previous.committed_offset or 0)
        delta_lag = (current.lag or 0) - (previous.lag or 0)

        return StuckPartition(
            cluster_id=current.cluster_id,
            group_id=current.group_id,
            topic=current.topic,
            partition=current.partition,
            assigned_member_id=current.assigned_member_id,
            since_ts=since_ts,
            detected_ts=current.ts,
            current_lag=current.lag or 0,
            delta_committed=delta_committed,
            delta_lag=delta_lag,
            epsilon=self._epsilon,
            theta=self._theta,
        )

    def detect_stuck_partitions(
        self,
        current_partitions: list[ConsumerPartition],
        previous_partitions: list[ConsumerPartition],
        existing_stuck: dict[tuple[str, str, str, int], datetime] | None = None,
    ) -> list[StuckPartition]:
        """배치 Stuck Partition 감지

        Args:
            current_partitions: 현재 파티션 목록
            previous_partitions: 이전 파티션 목록
            existing_stuck: 기존 stuck 파티션 맵 {(cluster, group, topic, partition): since_ts}

        Returns:
            StuckPartition 목록
        """
        if existing_stuck is None:
            existing_stuck = {}

        # 이전 파티션 맵 생성
        prev_map: dict[tuple[str, str, str, int], ConsumerPartition] = {
            (p.cluster_id, p.group_id, p.topic, p.partition): p for p in previous_partitions
        }

        stuck_partitions: list[StuckPartition] = []
        now = datetime.now()

        for current in current_partitions:
            key = (current.cluster_id, current.group_id, current.topic, current.partition)
            previous = prev_map.get(key)

            if self.is_stuck(current, previous):
                # 기존 stuck인지 확인
                since_ts = existing_stuck.get(key)

                if since_ts is None:
                    # 신규 stuck
                    since_ts = current.ts
                    existing_stuck[key] = since_ts

                # 최소 지속 시간 체크
                duration = (now - since_ts).total_seconds()
                if duration >= self._min_duration:
                    stuck = self.create_stuck_partition(current, previous, since_ts)  # type: ignore
                    stuck_partitions.append(stuck)
            else:
                # stuck 해제
                if key in existing_stuck:
                    del existing_stuck[key]

        return stuck_partitions
