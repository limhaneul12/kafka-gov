"""Consumer Metrics Response Schemas

메트릭 및 권고 응답용 Pydantic 스키마
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class FairnessIndexResponse(BaseModel):
    """Fairness Index 응답"""

    model_config = ConfigDict(
        frozen=True,
        json_schema_extra={
            "example": {
                "gini_coefficient": 0.15,
                "level": "Balanced",
                "member_count": 5,
                "avg_tp_per_member": 6.0,
                "max_tp_per_member": 7,
                "min_tp_per_member": 5,
            }
        },
    )

    gini_coefficient: float = Field(description="지니 계수 (0.0 ~ 1.0)")
    level: str = Field(description="균형 수준 (Balanced/Slight Skew/Hotspot)")
    member_count: int = Field(description="멤버 수")
    avg_tp_per_member: float = Field(description="멤버당 평균 파티션 수")
    max_tp_per_member: int = Field(description="최대 파티션 수")
    min_tp_per_member: int = Field(description="최소 파티션 수")


class RebalanceScoreResponse(BaseModel):
    """Rebalance Score 응답"""

    model_config = ConfigDict(frozen=True)

    score: float = Field(description="안정성 점수 (0 ~ 100, 높을수록 안정)")
    rebalances_per_hour: float = Field(description="시간당 리밸런스 횟수")
    stable_ratio: float | None = Field(None, description="안정 유지 비율")
    window: str = Field(description="집계 윈도우 (5m/1h)")


class ConsumerGroupAdviceResponse(BaseModel):
    """정책 권고 응답"""

    model_config = ConfigDict(
        frozen=True,
        json_schema_extra={
            "example": {
                "assignor_recommendation": "cooperative-sticky",
                "assignor_reason": "Incremental rebalancing으로 처리 중단 최소화",
                "static_membership_recommended": False,
                "static_membership_reason": None,
                "scale_recommendation": None,
                "scale_reason": None,
                "slo_compliance_rate": 1.0,
                "risk_eta": None,
            }
        },
    )

    assignor_recommendation: str | None = Field(None, description="Assignor 권장사항")
    assignor_reason: str | None = Field(None, description="Assignor 권장 이유")
    static_membership_recommended: bool = Field(description="Static Membership 권장 여부")
    static_membership_reason: str | None = Field(None, description="Static Membership 권장 이유")
    scale_recommendation: str | None = Field(
        None, description="Scale 권장사항 (increase_consumers/add_partitions)"
    )
    scale_reason: str | None = Field(None, description="Scale 권장 이유")
    slo_compliance_rate: float = Field(description="SLO 준수율 (0.0 ~ 1.0)")
    risk_eta: datetime | None = Field(None, description="위반 예상 시각 (ETA)")


class ConsumerGroupMetricsResponse(BaseModel):
    """Consumer Group 메트릭 응답"""

    model_config = ConfigDict(frozen=True)

    cluster_id: str = Field(description="클러스터 ID")
    group_id: str = Field(description="Consumer Group ID")
    fairness: FairnessIndexResponse = Field(description="Fairness Index")
    rebalance_score: RebalanceScoreResponse | None = Field(None, description="Rebalance Score")
    advice: ConsumerGroupAdviceResponse = Field(description="정책 권고")
