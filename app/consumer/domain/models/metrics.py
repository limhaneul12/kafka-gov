"""Consumer Metrics Domain Models

계산된 메트릭 Value Objects
- FairnessIndex: 부하 편중 지표 (cal.md 4️⃣)
- SLOCompliance: SLO 준수율 (cal.md 5️⃣)
- DeliveryRisk: 위험 예측 (cal.md 6️⃣)
- ConsumerGroupAdvice: 정책 권고 (cal.md 7️⃣)

참고: cal.md - 전체 계산 공식
"""

from dataclasses import dataclass
from datetime import datetime

from app.consumer.domain.types_enum import FairnessLevel


@dataclass(frozen=True, slots=True, kw_only=True)
class FairnessIndex:
    """부하 편중 지표 Value Object

    계산 공식 (cal.md 4️⃣):
    G = Σ_i Σ_j |x_i - x_j| / (2 * n^2 * mean(x))
    """

    gini_coefficient: float  # 지니계수 (0.0 ~ 1.0)
    member_count: int  # 멤버 수
    avg_tp_per_member: float  # 멤버당 평균 파티션 수
    max_tp_per_member: int  # 최대 파티션 수
    min_tp_per_member: int  # 최소 파티션 수

    def level(self) -> FairnessLevel:
        """균형 수준"""
        if self.gini_coefficient <= 0.2:
            return FairnessLevel.BALANCED
        elif self.gini_coefficient <= 0.4:
            return FairnessLevel.SLIGHT_SKEW
        else:
            return FairnessLevel.HOTSPOT

    def is_balanced(self) -> bool:
        """균형 상태 여부"""
        return self.gini_coefficient <= 0.2

    def has_hotspot(self) -> bool:
        """핫스팟 존재 여부"""
        return self.gini_coefficient > 0.4


@dataclass(frozen=True, slots=True, kw_only=True)
class ConsumerGroupAdvice:
    """정책 권고 Value Object

    정책 권고 결과 (cal.md 7️⃣)
    """

    # Assignor 권고
    assignor_recommendation: str | None  # cooperative-sticky 권장
    assignor_reason: str | None

    # Static membership 권고
    static_membership_recommended: bool
    static_membership_reason: str | None

    # Scale/Repartition 권고
    scale_recommendation: str | None  # "increase_consumers" | "add_partitions"
    scale_reason: str | None

    # SLO 준수율
    slo_compliance_rate: float  # p95_lag ≤ target_ms 비율

    # Delivery Risk ETA
    risk_eta: datetime | None  # lag 추세 기반 위반 예상 시각

    def needs_action(self) -> bool:
        """조치 필요 여부"""
        return (
            self.assignor_recommendation is not None
            or self.static_membership_recommended
            or self.scale_recommendation is not None
        )
