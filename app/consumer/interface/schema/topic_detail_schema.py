"""Topic Detail with Consumer Health Schema

토픽 상세 정보 + Consumer Health를 통합한 거버넌스 응답 스키마
"""

from pydantic import BaseModel, ConfigDict, Field


class ConsumerHealthSummary(BaseModel):
    """Consumer Group Health 요약"""

    model_config = ConfigDict(frozen=True)

    group_id: str = Field(description="Consumer Group ID")
    state: str = Field(description="그룹 상태 (Stable, Rebalancing, etc)")
    slo_compliance: float = Field(description="SLO 준수율 (0.0-1.0)", ge=0.0, le=1.0)
    lag_p50: int = Field(description="P50 Lag")
    lag_p95: int = Field(description="P95 Lag")
    lag_max: int = Field(description="Max Lag")
    stuck_count: int = Field(description="Stuck Partition 개수", ge=0)
    rebalance_score: float | None = Field(
        None, description="Rebalance 안정성 점수 (0-100, 이력 데이터 없으면 null)"
    )
    fairness_gini: float = Field(description="Fairness Gini 계수 (0-1)", ge=0, le=1)
    member_count: int = Field(description="멤버 수", ge=0)
    recommendation: str | None = Field(None, description="권장사항")


class GovernanceAlert(BaseModel):
    """거버넌스 경고"""

    model_config = ConfigDict(frozen=True)

    severity: str = Field(description="경고 수준 (info, warning, error)")
    consumer_group: str = Field(description="관련 Consumer Group")
    message: str = Field(description="경고 메시지")
    metric: str | None = Field(None, description="관련 메트릭 (slo, stuck, rebalance, fairness)")


class TopicConsumerInsight(BaseModel):
    """토픽 Consumer 전체 인사이트"""

    model_config = ConfigDict(frozen=True)

    total_consumers: int = Field(description="총 Consumer Group 수", ge=0)
    healthy_consumers: int = Field(description="정상 Consumer 수", ge=0)
    unhealthy_consumers: int = Field(description="비정상 Consumer 수", ge=0)
    avg_slo_compliance: float = Field(description="평균 SLO 준수율", ge=0, le=1)
    avg_rebalance_score: float = Field(description="평균 Rebalance 점수", ge=0, le=100)
    total_stuck_partitions: int = Field(description="전체 Stuck Partition 수", ge=0)
    partitions_with_consumers: int = Field(description="소비되고 있는 파티션 수", ge=0)
    total_partitions: int = Field(description="전체 파티션 수", ge=0)
    summary: str = Field(description="한 줄 요약")


class TopicDetailWithConsumerHealthResponse(BaseModel):
    """토픽 상세 정보 with Consumer Health (거버넌스)"""

    model_config = ConfigDict(
        frozen=True,
        json_schema_extra={
            "example": {
                "topic": "prod.orders.created",
                "cluster_id": "prod-cluster-01",
                "partitions": 12,
                "replication_factor": 3,
                "retention_ms": 604800000,
                "insight": {
                    "total_consumers": 3,
                    "healthy_consumers": 1,
                    "unhealthy_consumers": 2,
                    "avg_slo_compliance": 0.88,
                    "avg_rebalance_score": 72.5,
                    "total_stuck_partitions": 2,
                    "partitions_with_consumers": 12,
                    "total_partitions": 12,
                    "summary": "3개 Consumer Group 중 2개가 SLO 미달 상태입니다",
                },
                "consumer_groups": [
                    {
                        "group_id": "order-processor",
                        "state": "Stable",
                        "slo_compliance": 0.98,
                        "lag_p50": 120,
                        "lag_p95": 450,
                        "lag_max": 800,
                        "stuck_count": 0,
                        "rebalance_score": 85.0,
                        "fairness_gini": 0.15,
                        "member_count": 3,
                        "recommendation": None,
                    },
                    {
                        "group_id": "new-consumer",
                        "state": "Stable",
                        "slo_compliance": 1.0,
                        "lag_p50": 10,
                        "lag_p95": 50,
                        "lag_max": 100,
                        "stuck_count": 0,
                        "rebalance_score": None,
                        "fairness_gini": 0.05,
                        "member_count": 2,
                        "recommendation": None,
                    },
                ],
                "governance_alerts": [
                    {
                        "severity": "warning",
                        "consumer_group": "analytics-consumer",
                        "message": "SLO 미달 (현재: 87.0%, 기준: 95%)",
                        "metric": "slo",
                    }
                ],
            }
        },
    )

    topic: str = Field(description="토픽 이름")
    cluster_id: str = Field(description="클러스터 ID")
    partitions: int = Field(description="파티션 수", ge=1)
    replication_factor: int = Field(description="Replication Factor", ge=1)
    retention_ms: int = Field(description="Retention 시간 (ms)", ge=0)

    # Consumer 전체 인사이트
    insight: TopicConsumerInsight = Field(description="Consumer 전체 인사이트")

    # Consumer Health 목록
    consumer_groups: list[ConsumerHealthSummary] = Field(description="Consumer Group Health 목록")

    # 거버넌스 경고
    governance_alerts: list[GovernanceAlert] = Field(description="거버넌스 경고 목록")
