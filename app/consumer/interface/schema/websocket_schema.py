"""WebSocket Event Schemas

실시간 이벤트 스트림용 Pydantic 스키마 (Kafka-Gov WebSocket Spec v1)

모든 이벤트는 공통 헤더(type, version, ts, trace_id)를 포함합니다.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class BaseEvent(BaseModel):
    """WebSocket 이벤트 공통 베이스"""

    model_config = ConfigDict(frozen=True)

    type: str = Field(description="이벤트 타입")
    version: str = Field(default="v1", description="페이로드 버전")
    ts: datetime = Field(description="ISO8601 생성 시각")
    trace_id: UUID = Field(description="멱등/추적용 UUID")


# ============================================================================
# 1. 그룹 상태 전환
# ============================================================================


class GroupStateChangedEvent(BaseEvent):
    """그룹 상태 변경 이벤트"""

    model_config = ConfigDict(
        frozen=True,
        json_schema_extra={
            "example": {
                "type": "group_state_changed",
                "version": "v1",
                "ts": "2025-10-28T07:10:00Z",
                "trace_id": "550e8400-e29b-41d4-a716-446655440000",
                "group_id": "team-order-service",
                "old_state": "Stable",
                "new_state": "Rebalancing",
                "reason": "member_join",
            }
        },
    )

    type: str = Field(default="group_state_changed", description="이벤트 타입")
    group_id: str = Field(description="Consumer Group ID")
    old_state: str = Field(description="이전 상태")
    new_state: str = Field(description="새 상태")
    reason: str = Field(description="변경 이유: member_join|member_leave|assignor_change|unknown")


# ============================================================================
# 2. 라그 급증 (Lag Spike)
# ============================================================================


class LagSpikeEvent(BaseEvent):
    """라그 급증 이벤트"""

    model_config = ConfigDict(
        frozen=True,
        json_schema_extra={
            "example": {
                "type": "lag_spike",
                "version": "v1",
                "ts": "2025-10-28T07:10:00Z",
                "trace_id": "550e8400-e29b-41d4-a716-446655440001",
                "group_id": "team-order-service",
                "delta_total_lag": 4200,
                "current": {"total_lag": 8200, "p95_lag": 950, "max_lag": 2400},
                "window_s": 60,
                "thresholds": {"delta_total_lag": 2000},
            }
        },
    )

    type: str = Field(default="lag_spike", description="이벤트 타입")
    group_id: str = Field(description="Consumer Group ID")
    delta_total_lag: int = Field(description="total lag 증가량")
    current: dict[str, int] = Field(description="현재 lag 통계 (total_lag, p95_lag, max_lag)")
    window_s: int = Field(description="감지 윈도우(초)")
    thresholds: dict[str, int] = Field(description="트리거 기준 (선택)")


# ============================================================================
# 3. 스턱 파티션 감지
# ============================================================================


class StuckDetectedEvent(BaseEvent):
    """Stuck Partition 감지 이벤트"""

    model_config = ConfigDict(
        frozen=True,
        json_schema_extra={
            "example": {
                "type": "stuck_detected",
                "version": "v1",
                "ts": "2025-10-28T07:10:00Z",
                "trace_id": "550e8400-e29b-41d4-a716-446655440002",
                "group_id": "team-order-service",
                "topic": "orders",
                "partition": 7,
                "member_id": "consumer-3",
                "since": "2025-10-28T07:05:00Z",
                "lag": 4520,
                "rule": {
                    "delta_committed_le": 1,
                    "delta_lag_ge": 10,
                    "duration_s_ge": 180,
                },
            }
        },
    )

    type: str = Field(default="stuck_detected", description="이벤트 타입")
    group_id: str = Field(description="Consumer Group ID")
    topic: str = Field(description="토픽 이름")
    partition: int = Field(description="파티션 번호")
    member_id: str | None = Field(None, description="담당 멤버 ID")
    since: datetime = Field(description="Stuck 시작 시각")
    lag: int = Field(description="현재 lag")
    rule: dict[str, int] = Field(description="감지 규칙")


# ============================================================================
# 4. 리밸런스 델타 (할당 변경 요약)
# ============================================================================


class AssignmentChangedEvent(BaseEvent):
    """리밸런스 델타(할당 변경 요약) 이벤트"""

    model_config = ConfigDict(
        frozen=True,
        json_schema_extra={
            "example": {
                "type": "assignment_changed",
                "version": "v1",
                "ts": "2025-10-28T07:10:00Z",
                "trace_id": "550e8400-e29b-41d4-a716-446655440003",
                "group_id": "team-order-service",
                "moved_partitions": 6,
                "join_count": 1,
                "leave_count": 0,
                "movement_rate": 0.047,
                "stable_elapsed_s": 380,
                "assignment_hash": "c0ffee1234567890",
            }
        },
    )

    type: str = Field(default="assignment_changed", description="이벤트 타입")
    group_id: str = Field(description="Consumer Group ID")
    moved_partitions: int = Field(description="이동한 파티션 수")
    join_count: int = Field(description="조인한 멤버 수")
    leave_count: int = Field(description="떠난 멤버 수")
    movement_rate: float = Field(description="moved / total_partitions")
    stable_elapsed_s: int = Field(description="안정 상태 유지 시간(초)")
    assignment_hash: str = Field(description="할당 해시")


# ============================================================================
# 5. 공평성/핫스팟 경고
# ============================================================================


class FairnessWarnEvent(BaseEvent):
    """공평성/핫스팟 경고 이벤트"""

    model_config = ConfigDict(
        frozen=True,
        json_schema_extra={
            "example": {
                "type": "fairness_warn",
                "version": "v1",
                "ts": "2025-10-28T07:10:00Z",
                "trace_id": "550e8400-e29b-41d4-a716-446655440004",
                "group_id": "team-order-service",
                "gini": 0.46,
                "hint": "Add 1 consumer or rebalance keys",
                "thresholds": {"gini_warn": 0.4},
            }
        },
    )

    type: str = Field(default="fairness_warn", description="이벤트 타입")
    group_id: str = Field(description="Consumer Group ID")
    gini: float = Field(description="Gini 계수")
    hint: str = Field(description="개선 제안")
    thresholds: dict[str, float] = Field(description="임계치")


# ============================================================================
# 6. 어드바이저 (정책/전략 권고)
# ============================================================================


class AdvisorEvent(BaseEvent):
    """어드바이저(정책/전략 권고) 이벤트"""

    model_config = ConfigDict(
        frozen=True,
        json_schema_extra={
            "example": {
                "type": "advisor",
                "version": "v1",
                "ts": "2025-10-28T07:10:00Z",
                "trace_id": "550e8400-e29b-41d4-a716-446655440005",
                "group_id": "team-order-service",
                "advice": [
                    {"kind": "assignor", "level": "recommend", "message": "Use cooperative-sticky"},
                    {
                        "kind": "static-membership",
                        "level": "must",
                        "message": "Enable group.instance.id",
                    },
                ],
            }
        },
    )

    type: str = Field(default="advisor", description="이벤트 타입")
    group_id: str = Field(description="Consumer Group ID")
    advice: list[dict[str, str]] = Field(description="권고 목록 (kind, level, message)")


# ============================================================================
# 7. 시스템 상태 (선택)
# ============================================================================


class SystemHealthEvent(BaseEvent):
    """시스템 상태 이벤트"""

    model_config = ConfigDict(
        frozen=True,
        json_schema_extra={
            "example": {
                "type": "system_health",
                "version": "v1",
                "ts": "2025-10-28T07:10:00Z",
                "trace_id": "550e8400-e29b-41d4-a716-446655440006",
                "collector_ok": True,
                "broker_ok": True,
            }
        },
    )

    type: str = Field(default="system_health", description="이벤트 타입")
    collector_ok: bool = Field(description="수집기 정상 여부")
    broker_ok: bool = Field(description="브로커 정상 여부")
