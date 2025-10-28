"""Consumer Detail Response Schemas

추가 상세 정보용 Pydantic 스키마
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ConsumerGroupSummaryResponse(BaseModel):
    """Consumer Group 상세 요약 응답 (job.md 스펙)"""

    model_config = ConfigDict(
        frozen=True,
        json_schema_extra={
            "example": {
                "group_id": "order-processor",
                "cluster_id": "prod-cluster-01",
                "state": "Stable",
                "member_count": 3,
                "topic_count": 5,
                "lag": {
                    "p50": 450,
                    "p95": 1200,
                    "max": 2500,
                    "total": 15234,
                },
                "rebalance_score": None,
                "fairness_gini": 0.15,
                "stuck": [],
            }
        },
    )

    group_id: str = Field(description="Consumer Group ID")
    cluster_id: str = Field(description="클러스터 ID")
    state: str = Field(description="그룹 상태")
    member_count: int = Field(description="멤버 수", ge=0)
    topic_count: int = Field(description="구독 중인 토픽 수", ge=0)
    lag: dict[str, int] = Field(description="Lag 통계 (p50, p95, max, total)")
    rebalance_score: float | None = Field(
        None, description="리밸런스 안정성 점수 (0-100, 이력 데이터 없으면 null)"
    )
    fairness_gini: float = Field(description="Fairness Gini 계수")
    stuck: list[dict] = Field(description="멈춘 파티션 목록")


class MemberDetailResponse(BaseModel):
    """멤버 상세 정보"""

    model_config = ConfigDict(frozen=True)

    member_id: str = Field(description="멤버 ID")
    client_id: str | None = Field(None, description="클라이언트 ID")
    client_host: str | None = Field(None, description="호스트 IP")
    assigned_partitions: list[dict[str, int | str]] = Field(
        description="할당된 파티션 목록 [{topic, partition}]"
    )


class PartitionDetailResponse(BaseModel):
    """파티션 상세 정보"""

    model_config = ConfigDict(frozen=True)

    topic: str = Field(description="토픽 이름")
    partition: int = Field(description="파티션 번호")
    committed_offset: int | None = Field(None, description="커밋 오프셋")
    latest_offset: int | None = Field(None, description="최신 오프셋")
    lag: int | None = Field(None, description="Lag")
    assigned_member_id: str | None = Field(None, description="담당 멤버 ID")


class TopicConsumerMappingResponse(BaseModel):
    """토픽별 컨슈머 매핑 정보"""

    model_config = ConfigDict(frozen=True)

    topic: str = Field(description="토픽 이름")
    consumer_groups: list[dict] = Field(description="해당 토픽을 읽는 그룹/멤버/파티션 매핑")


class RebalanceEventResponse(BaseModel):
    """리밸런스 이벤트 정보"""

    model_config = ConfigDict(
        frozen=True,
        json_schema_extra={
            "example": {
                "ts": "2025-10-27T23:45:00Z",
                "moved_partitions": 12,
                "join_count": 1,
                "leave_count": 0,
                "elapsed_since_prev_s": 3600,
                "state": "Stable",
            }
        },
    )

    ts: datetime = Field(description="리밸런스 발생 시각")
    moved_partitions: int = Field(description="이동한 파티션 수")
    join_count: int = Field(description="참여한 멤버 수")
    leave_count: int = Field(description="떠난 멤버 수")
    elapsed_since_prev_s: int | None = Field(None, description="직전 리밸런스 이후 경과 시간(초)")
    state: str = Field(description="리밸런스 후 상태")


class PolicyAdviceResponse(BaseModel):
    """정책 어드바이저 응답"""

    model_config = ConfigDict(frozen=True)

    assignor: dict[str, str | None] = Field(
        description="Assignor 권장사항 {recommendation, reason}"
    )
    static_membership: dict[str, bool | str | None] = Field(
        description="Static Membership 권장 {recommended, reason}"
    )
    scale: dict[str, str | None] = Field(description="Scale 권장사항 {recommendation, reason}")
    slo_compliance: float = Field(description="SLO 준수율")
    risk_eta: datetime | None = Field(None, description="위반 예상 시각")
