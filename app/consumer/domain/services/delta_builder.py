"""Delta Builder Service

이전 상태와 현재 상태를 비교하여 변경분(델타)을 계산하고 이벤트를 생성합니다.

Collector → Delta Builder → WebSocket Broadcaster 파이프라인
"""

import hashlib
from datetime import datetime
from uuid import uuid4

from app.consumer.domain.models import ConsumerGroup
from app.consumer.domain.thresholds import DEFAULT_THRESHOLDS, ConsumerThresholds


class DeltaBuilder:
    """Consumer Group 델타 계산 및 이벤트 생성"""

    def __init__(self, thresholds: ConsumerThresholds = DEFAULT_THRESHOLDS) -> None:
        """
        Args:
            thresholds: 임계치 설정
        """
        self._thresholds = thresholds
        self._previous_states: dict[str, dict] = {}  # group_id -> 이전 상태

    def calculate_delta(
        self, current_group: ConsumerGroup, previous_state: dict | None = None
    ) -> list[dict]:
        """그룹의 델타를 계산하고 이벤트 목록 반환

        Args:
            current_group: 현재 그룹 상태
            previous_state: 이전 상태 (없으면 내부 캐시 사용)

        Returns:
            이벤트 dict 리스트 (공통 헤더 포함)
        """
        events: list[dict] = []
        group_id = current_group.group_id

        # 이전 상태 가져오기
        if previous_state is None:
            previous_state = self._previous_states.get(group_id)

        # 이전 상태가 없으면 초기화만 하고 이벤트 생성 안함
        if previous_state is None:
            self._store_current_state(current_group)
            return events

        # 1. 상태 전환 감지
        if current_group.state.value != previous_state.get("state"):
            events.append(self._build_state_changed_event(current_group, previous_state))

        # 2. Lag Spike 감지
        delta_total_lag = current_group.lag_stats.total_lag - previous_state.get("total_lag", 0)
        if delta_total_lag >= self._thresholds.lag.spike_delta_total_lag:
            events.append(self._build_lag_spike_event(current_group, delta_total_lag))

        # 3. Fairness 경고 (Gini 계수)
        # Note: Fairness는 멤버/파티션 정보가 필요하므로 별도 메서드로 처리
        # 여기서는 기본 그룹 레벨 델타만 처리

        # 현재 상태 저장
        self._store_current_state(current_group)

        return events

    def _build_state_changed_event(self, current: ConsumerGroup, previous: dict) -> dict:
        """그룹 상태 변경 이벤트 생성"""
        reason = "unknown"
        current_assignor_val = (
            current.partition_assignor.value if current.partition_assignor else None
        )
        if current.member_count > previous.get("member_count", 0):
            reason = "member_join"
        elif current.member_count < previous.get("member_count", 0):
            reason = "member_leave"
        elif current_assignor_val != previous.get("partition_assignor"):
            reason = "assignor_change"

        return {
            "type": "group_state_changed",
            "version": "v1",
            "ts": datetime.utcnow().isoformat(),
            "trace_id": str(uuid4()),
            "group_id": current.group_id,
            "old_state": previous.get("state", "Unknown"),
            "new_state": current.state.value,
            "reason": reason,
        }

    def _build_lag_spike_event(self, current: ConsumerGroup, delta_total_lag: int) -> dict:
        """Lag Spike 이벤트 생성"""
        return {
            "type": "lag_spike",
            "version": "v1",
            "ts": datetime.utcnow().isoformat(),
            "trace_id": str(uuid4()),
            "group_id": current.group_id,
            "delta_total_lag": delta_total_lag,
            "current": {
                "total_lag": current.lag_stats.total_lag,
                "p95_lag": current.lag_stats.p95_lag,
                "max_lag": current.lag_stats.max_lag,
            },
            "window_s": self._thresholds.lag.spike_window_s,
            "thresholds": {"delta_total_lag": self._thresholds.lag.spike_delta_total_lag},
        }

    def build_assignment_changed_event(
        self,
        group_id: str,
        moved_partitions: int,
        join_count: int,
        leave_count: int,
        total_partitions: int,
        stable_elapsed_s: int,
        assignment_partitions: list[tuple[str, int]],
    ) -> dict:
        """리밸런스 델타(할당 변경) 이벤트 생성

        Args:
            group_id: Consumer Group ID
            moved_partitions: 이동한 파티션 수
            join_count: 조인한 멤버 수
            leave_count: 떠난 멤버 수
            total_partitions: 전체 파티션 수
            stable_elapsed_s: 안정 상태 유지 시간(초)
            assignment_partitions: 할당 파티션 목록 (topic, partition)
        """
        # 할당 해시 계산
        assignment_str = ",".join(f"{t}:{p}" for t, p in sorted(assignment_partitions))
        assignment_hash = hashlib.sha256(assignment_str.encode()).hexdigest()[:16]

        movement_rate = moved_partitions / total_partitions if total_partitions > 0 else 0.0

        return {
            "type": "assignment_changed",
            "version": "v1",
            "ts": datetime.utcnow().isoformat(),
            "trace_id": str(uuid4()),
            "group_id": group_id,
            "moved_partitions": moved_partitions,
            "join_count": join_count,
            "leave_count": leave_count,
            "movement_rate": round(movement_rate, 4),
            "stable_elapsed_s": stable_elapsed_s,
            "assignment_hash": assignment_hash,
        }

    def build_stuck_detected_event(
        self,
        group_id: str,
        topic: str,
        partition: int,
        member_id: str | None,
        since: datetime,
        lag: int,
    ) -> dict:
        """Stuck Partition 감지 이벤트 생성"""
        return {
            "type": "stuck_detected",
            "version": "v1",
            "ts": datetime.utcnow().isoformat(),
            "trace_id": str(uuid4()),
            "group_id": group_id,
            "topic": topic,
            "partition": partition,
            "member_id": member_id,
            "since": since.isoformat(),
            "lag": lag,
            "rule": {
                "delta_committed_le": self._thresholds.stuck.delta_committed_le,
                "delta_lag_ge": self._thresholds.stuck.delta_lag_ge,
                "duration_s_ge": self._thresholds.stuck.duration_s_ge,
            },
        }

    def build_fairness_warn_event(self, group_id: str, gini: float, hint: str) -> dict:
        """공평성/핫스팟 경고 이벤트 생성"""
        return {
            "type": "fairness_warn",
            "version": "v1",
            "ts": datetime.utcnow().isoformat(),
            "trace_id": str(uuid4()),
            "group_id": group_id,
            "gini": round(gini, 4),
            "hint": hint,
            "thresholds": {"gini_warn": self._thresholds.fairness.gini_warn},
        }

    def build_advisor_event(self, group_id: str, advice_list: list[dict[str, str]]) -> dict:
        """어드바이저(정책/전략 권고) 이벤트 생성

        Args:
            group_id: Consumer Group ID
            advice_list: [{"kind": str, "level": str, "message": str}, ...]
        """
        return {
            "type": "advisor",
            "version": "v1",
            "ts": datetime.utcnow().isoformat(),
            "trace_id": str(uuid4()),
            "group_id": group_id,
            "advice": advice_list,
        }

    def build_system_health_event(self, collector_ok: bool, broker_ok: bool) -> dict:
        """시스템 상태 이벤트 생성"""
        return {
            "type": "system_health",
            "version": "v1",
            "ts": datetime.utcnow().isoformat(),
            "trace_id": str(uuid4()),
            "collector_ok": collector_ok,
            "broker_ok": broker_ok,
        }

    def _store_current_state(self, group: ConsumerGroup) -> None:
        """현재 상태를 저장 (다음 델타 계산용)"""
        self._previous_states[group.group_id] = {
            "state": group.state.value,
            "member_count": group.member_count,
            "total_lag": group.lag_stats.total_lag,
            "p95_lag": group.lag_stats.p95_lag,
            "max_lag": group.lag_stats.max_lag,
            "partition_assignor": group.partition_assignor.value
            if group.partition_assignor
            else None,
            "ts": group.ts,
        }
