"""Consumer Thresholds Configuration

WebSocket 이벤트 임계치 설정 (YAML 기반 런타임 변경 가능)
"""

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class LagThresholds:
    """Lag 관련 임계치"""

    spike_delta_total_lag: int = 2000  # total lag 증가량 임계치
    spike_window_s: int = 60  # 감지 윈도우(초)


@dataclass(frozen=True, slots=True)
class StuckThresholds:
    """Stuck Partition 임계치"""

    delta_committed_le: int = 1  # committed offset 변화량 ≤
    delta_lag_ge: int = 10  # lag 증가량 ≥
    duration_s_ge: int = 180  # 지속 시간 ≥ (초)


@dataclass(frozen=True, slots=True)
class RebalanceThresholds:
    """Rebalance 관련 임계치"""

    rate_warn_per_hour: int = 4  # 시간당 리밸런스 횟수 경고
    movement_rate_warn: float = 0.10  # 이동 비율 경고 (moved / total)


@dataclass(frozen=True, slots=True)
class FairnessThresholds:
    """Fairness 관련 임계치"""

    gini_warn: float = 0.40  # Gini 계수 경고 임계치


@dataclass(frozen=True, slots=True)
class ConsumerThresholds:
    """전체 Consumer 임계치 설정"""

    lag: LagThresholds = field(default_factory=LagThresholds)
    stuck: StuckThresholds = field(default_factory=StuckThresholds)
    rebalance: RebalanceThresholds = field(default_factory=RebalanceThresholds)
    fairness: FairnessThresholds = field(default_factory=FairnessThresholds)


# 기본 임계치 인스턴스
DEFAULT_THRESHOLDS = ConsumerThresholds()
