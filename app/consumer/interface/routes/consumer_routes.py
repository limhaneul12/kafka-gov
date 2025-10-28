"""Consumer API Routes

Consumer Group Governance API 엔드포인트 (job.md 스펙 준수)

REST API (7개):
- GET /api/v1/consumers/groups - 전체 그룹 목록
- GET /api/v1/consumers/groups/{group}/summary - 그룹 상세 요약
- GET /api/v1/consumers/groups/{group}/members - 멤버 목록
- GET /api/v1/consumers/groups/{group}/partitions - 파티션 목록
- GET /api/v1/topics/{topic}/consumers - 토픽별 컨슈머 매핑
- GET /api/v1/consumers/groups/{group}/rebalance - 리밸런스 이벤트
- GET /api/v1/consumers/groups/{group}/advice - 정책 어드바이저
"""

import asyncio
from typing import Annotated

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Path, Query, status

from app.cluster.domain.services import ConnectionManager
from app.consumer.application.use_cases import (
    GetConsumerGroupMetricsUseCase,
    GetConsumerGroupSummaryUseCase,
    GetGroupAdviceUseCase,
    GetGroupMembersUseCase,
    GetGroupPartitionsUseCase,
    GetGroupRebalanceUseCase,
    GetGroupTopicStatsUseCase,
    GetTopicConsumersUseCase,
)
from app.consumer.domain.services.collector import ConsumerDataCollector
from app.consumer.infrastructure.kafka_consumer_adapter import KafkaConsumerAdapter
from app.consumer.interface.schema import (
    ConsumerGroupListResponse,
    ConsumerGroupMetricsResponse,
    ConsumerGroupResponse,
    LagStatsResponse,
)
from app.consumer.interface.schema.detail_schema import (
    ConsumerGroupSummaryResponse,
    MemberDetailResponse,
    PartitionDetailResponse,
    PolicyAdviceResponse,
    RebalanceEventResponse,
    TopicConsumerMappingResponse,
)
from app.consumer.interface.schema.topic_stats_schema import GroupTopicStatsResponse
from app.container import AppContainer
from app.shared.error_handlers import handle_server_errors

router = APIRouter(prefix="/api/v1/consumers", tags=["Consumer Groups"])

# Dependency Injection Shortcuts
GetMetricsDep = Depends(Provide[AppContainer.consumer_container.get_metrics_use_case])
GetSummaryDep = Depends(Provide[AppContainer.consumer_container.get_summary_use_case])
MembersDep = Depends(Provide[AppContainer.consumer_container.get_members_use_case])
PartitionsDep = Depends(Provide[AppContainer.consumer_container.get_partitions_use_case])
RebalanceDep = Depends(Provide[AppContainer.consumer_container.get_rebalance_use_case])
AdviceDep = Depends(Provide[AppContainer.consumer_container.get_advice_use_case])
TopicStatsDep = Depends(Provide[AppContainer.consumer_container.get_group_topic_stats_use_case])
TopicConsumersDep = Depends(Provide[AppContainer.consumer_container.get_topic_consumers_use_case])
ConnectionManagerDep = Depends(Provide[AppContainer.cluster_container.connection_manager])


@router.get(
    "/groups",
    response_model=ConsumerGroupListResponse,
    status_code=status.HTTP_200_OK,
    summary="Consumer Group 목록 조회 (실시간)",
    description="Kafka에서 직접 Consumer Group 목록과 최신 상태를 실시간으로 조회합니다.",
)
@inject
@handle_server_errors(error_message="Failed to list consumer groups")
async def list_consumer_groups(
    cluster_id: str = Query(..., description="클러스터 ID"),
    connection_manager: ConnectionManager = ConnectionManagerDep,
) -> ConsumerGroupListResponse:
    """Consumer Group 목록 실시간 조회 (Kafka AdminClient 사용)

    KafkaConsumerAdapter를 사용하여 실시간으로 조회
    - asyncio.to_thread로 비동기 처리
    - Future.result() 올바르게 처리
    """
    # 1. Kafka AdminClient 가져오기
    admin_client = await connection_manager.get_kafka_admin_client(cluster_id)

    # 2. KafkaConsumerAdapter로 래핑
    adapter = KafkaConsumerAdapter(admin_client)

    # 3. ConsumerDataCollector 생성 (실제 Lag 통계 계산)
    collector = ConsumerDataCollector(adapter, cluster_id)

    # 4. Consumer Groups 목록 조회 (비동기)
    consumer_groups = await adapter.list_consumer_groups()

    # 5. 병렬로 그룹 데이터 수집 (asyncio.gather, 예외 포함)
    group_data_list = await asyncio.gather(
        *[collector.collect_group(g.group_id) for g in consumer_groups],
        return_exceptions=True,  # 개별 그룹 에러를 예외 객체로 반환
    )

    # 6. Domain Model → Response DTO 변환 (에러 제외)
    groups: list[ConsumerGroupResponse] = []
    for group_data in group_data_list:
        if isinstance(group_data, BaseException):
            continue

        groups.append(
            ConsumerGroupResponse(
                cluster_id=group_data.cluster_id,
                group_id=group_data.group_id,
                ts=group_data.ts,
                state=group_data.state.value,
                partition_assignor=(
                    group_data.partition_assignor.value if group_data.partition_assignor else None
                ),
                member_count=group_data.member_count,
                topic_count=group_data.topic_count,
                lag_stats=LagStatsResponse(
                    total_lag=group_data.lag_stats.total_lag,
                    mean_lag=group_data.lag_stats.mean_lag,
                    p50_lag=group_data.lag_stats.p50_lag,
                    p95_lag=group_data.lag_stats.p95_lag,
                    max_lag=group_data.lag_stats.max_lag,
                    partition_count=group_data.lag_stats.partition_count,
                ),
            )
        )

    return ConsumerGroupListResponse(groups=groups, total=len(groups))


@router.get(
    "/groups/{group_id}/metrics",
    response_model=ConsumerGroupMetricsResponse,
    status_code=status.HTTP_200_OK,
    summary="Consumer Group 메트릭 조회",
    description="""
    Consumer Group의 상세 메트릭을 조회합니다.

    포함 항목:
    - Fairness Index (Gini Coefficient)
    - Rebalance Score
    - Policy Advice (Assignor, Static Membership, Scale-out)
    - SLO Compliance Rate
    - Delivery Risk ETA
    """,
)
@inject
@handle_server_errors(error_message="Failed to get consumer group metrics")
async def get_consumer_group_metrics(
    group_id: Annotated[str, Path(description="Consumer Group ID")],
    cluster_id: str = Query(..., description="클러스터 ID"),
    use_case: GetConsumerGroupMetricsUseCase = GetMetricsDep,
) -> ConsumerGroupMetricsResponse:
    """Consumer Group 메트릭 조회"""
    return await use_case.execute(cluster_id, group_id)


# ============================================================================
# job.md 스펙 추가 엔드포인트
# ============================================================================


@router.get(
    "/groups/{group}/summary",
    response_model=ConsumerGroupSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Consumer Group 상세 요약",
    description="그룹의 lag, rebalance_score, fairness_gini, stuck 파티션을 포함한 요약 정보",
)
@inject
@handle_server_errors(error_message="Failed to get group summary")
async def get_group_summary(
    group: Annotated[str, Path(description="Consumer Group ID")],
    cluster_id: str = Query(..., description="클러스터 ID"),
    use_case: GetConsumerGroupSummaryUseCase = GetSummaryDep,
) -> ConsumerGroupSummaryResponse:
    """Consumer Group 상세 요약 (job.md 스펙)

    TODO: GetGroupSummaryUseCase 구현 및 Container 등록 필요

    Returns:
        lag: {p50, p95, max, total}
        rebalance_score: 리밸런스 안정성 점수
        fairness_gini: Gini 계수
        stuck: 멈춘 파티션 목록
    """
    return await use_case.execute(cluster_id, group)


@router.get(
    "/groups/{group}/members",
    response_model=list[MemberDetailResponse],
    status_code=status.HTTP_200_OK,
    summary="Consumer Group 멤버 목록",
    description="그룹 내 멤버 / 호스트 / 할당 파티션 목록",
)
@inject
@handle_server_errors(error_message="Failed to get group members")
async def get_group_members(
    group: Annotated[str, Path(description="Consumer Group ID")],
    cluster_id: str = Query(..., description="클러스터 ID"),
    use_case: GetGroupMembersUseCase = MembersDep,
) -> list[MemberDetailResponse]:
    """멤버 목록 조회 (job.md 스펙)"""
    return await use_case.execute(cluster_id, group)


@router.get(
    "/groups/{group}/partitions",
    response_model=list[PartitionDetailResponse],
    status_code=status.HTTP_200_OK,
    summary="Consumer Group 파티션 목록",
    description="파티션별 committed, latest, lag, assigned_member_id",
)
@inject
@handle_server_errors(error_message="Failed to get group partitions")
async def get_group_partitions(
    group: Annotated[str, Path(description="Consumer Group ID")],
    cluster_id: str = Query(..., description="클러스터 ID"),
    use_case: GetGroupPartitionsUseCase = PartitionsDep,
) -> list[PartitionDetailResponse]:
    """파티션 목록 조회 (job.md 스펙)"""
    return await use_case.execute(cluster_id, group)


@router.get(
    "/groups/{group}/rebalance",
    response_model=list[RebalanceEventResponse],
    status_code=status.HTTP_200_OK,
    summary="리밸런스 이벤트 조회",
    description="최근 리밸런스 델타 (이동 수, join/leave, 유지시간 등)",
)
@inject
@handle_server_errors(error_message="Failed to get group rebalance events")
async def get_group_rebalance(
    group: Annotated[str, Path(description="Consumer Group ID")],
    cluster_id: str = Query(..., description="클러스터 ID"),
    limit: int = Query(10, description="조회 개수"),
    use_case: GetGroupRebalanceUseCase = RebalanceDep,
) -> list[RebalanceEventResponse]:
    """리밸런스 이벤트 조회 (job.md 스펙)"""
    return await use_case.execute(cluster_id, group, limit)


@router.get(
    "/groups/{group}/advice",
    response_model=PolicyAdviceResponse,
    status_code=status.HTTP_200_OK,
    summary="정책 어드바이저",
    description="Assignor, Static Membership, Scale-out 권장사항",
)
@inject
@handle_server_errors(error_message="Failed to get group advice")
async def get_group_advice(
    group: Annotated[str, Path(description="Consumer Group ID")],
    cluster_id: str = Query(..., description="클러스터 ID"),
    use_case: GetGroupAdviceUseCase = AdviceDep,
) -> PolicyAdviceResponse:
    """정책 어드바이저 (job.md 스펙)"""
    return await use_case.execute(cluster_id, group)


@router.get(
    "/groups/{group}/topic-stats",
    response_model=GroupTopicStatsResponse,
    status_code=status.HTTP_200_OK,
    summary="Consumer Group 토픽별 통계",
    description="해당 그룹이 소비하는 토픽별 lag 집계 통계 (Backend에서 계산)",
)
@inject
@handle_server_errors(error_message="Failed to get topic statistics")
async def get_group_topic_stats(
    group: Annotated[str, Path(description="Consumer Group ID")],
    cluster_id: str = Query(..., description="클러스터 ID"),
    use_case: GetGroupTopicStatsUseCase = TopicStatsDep,
) -> GroupTopicStatsResponse:
    """토픽별 집계 통계 조회 (Backend에서 계산)

    Frontend에서 집계하는 대신 Backend에서 계산하여 제공:
    - Total Lag
    - Avg Lag
    - Max Lag
    - Lag Share (전체 대비 비율)
    - Partition Count

    Result는 Total Lag 내림차순으로 정렬됨
    """
    return await use_case.execute(cluster_id, group)


# ============================================================================
# 토픽별 컨슈머 매핑 (별도 prefix)
# ============================================================================

topic_router = APIRouter(prefix="/api/v1/topics", tags=["Topics"])


@topic_router.get(
    "/{topic}/consumers",
    response_model=TopicConsumerMappingResponse,
    status_code=status.HTTP_200_OK,
    summary="토픽별 컨슈머 매핑",
    description="해당 토픽을 읽는 그룹/멤버/파티션 매핑",
)
@inject
@handle_server_errors(error_message="Failed to get topic consumers")
async def get_topic_consumers(
    topic: Annotated[str, Path(description="토픽 이름")],
    cluster_id: str = Query(..., description="클러스터 ID"),
    use_case: GetTopicConsumersUseCase = TopicConsumersDep,
) -> TopicConsumerMappingResponse:
    """토픽별 컨슈머 매핑 (job.md 스펙)"""
    return await use_case.execute(cluster_id, topic)
