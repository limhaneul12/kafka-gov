"""Shared Interface Router"""

from datetime import datetime
from typing import Any

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Query

from app.container import AppContainer
from app.shared.interface.schema import BrokerResponse, ClusterStatusResponse

router = APIRouter(prefix="/v1", tags=["shared"])


@router.get("/audit/recent")
@inject
async def get_recent_activities(
    use_case=Depends(Provide[AppContainer.infrastructure_container.get_recent_activities_use_case]),
    limit: int = Query(default=20, ge=1, le=100, description="조회할 활동 수"),
) -> list[dict[str, Any]]:
    """
    최근 활동 조회 (Topic + Schema Audit 통합)

    Args:
        limit: 조회할 활동 수 (1-100)

    Returns:
        최근 활동 목록 (시간 역순)
    """
    activities = await use_case.execute(limit=limit)

    # msgspec.Struct를 dict로 변환 (FastAPI가 자동으로 JSON 직렬화)
    result: list[dict[str, Any]] = []
    for activity in activities:
        activity_dict: dict[str, Any] = {
            "activity_type": activity.activity_type,
            "action": activity.action,
            "target": activity.target,
            "message": activity.message,
            "actor": activity.actor,
            "timestamp": activity.timestamp.isoformat(),
            "metadata": activity.metadata,
        }
        result.append(activity_dict)

    return result


@router.get("/audit/history")
@inject
async def get_activity_history(
    use_case=Depends(Provide[AppContainer.infrastructure_container.get_activity_history_use_case]),
    from_date: datetime | None = Query(default=None, description="시작 날짜/시간 (ISO 8601)"),
    to_date: datetime | None = Query(default=None, description="종료 날짜/시간 (ISO 8601)"),
    activity_type: str | None = Query(default=None, description="활동 타입 (topic/schema)"),
    action: str | None = Query(default=None, description="액션 타입"),
    actor: str | None = Query(default=None, description="수행자"),
    limit: int = Query(default=100, ge=1, le=500, description="최대 조회 개수"),
) -> list[dict[str, Any]]:
    """
    활동 히스토리 조회 (필터링 지원)

    Args:
        from_date: 시작 날짜/시간
        to_date: 종료 날짜/시간
        activity_type: 활동 타입 필터
        action: 액션 필터
        actor: 수행자 필터
        limit: 최대 조회 개수 (1-500)

    Returns:
        필터링된 활동 목록 (시간 역순)
    """
    activities = await use_case.execute(
        from_date=from_date,
        to_date=to_date,
        activity_type=activity_type,
        action=action,
        actor=actor,
        limit=limit,
    )

    # msgspec.Struct를 dict로 변환
    result: list[dict[str, Any]] = []
    for activity in activities:
        activity_dict: dict[str, Any] = {
            "activity_type": activity.activity_type,
            "action": activity.action,
            "target": activity.target,
            "message": activity.message,
            "actor": activity.actor,
            "timestamp": activity.timestamp.isoformat(),
            "metadata": activity.metadata,
        }
        result.append(activity_dict)

    return result


@router.get("/cluster/status", response_model=ClusterStatusResponse)
@inject
async def get_cluster_status(
    use_case=Depends(Provide[AppContainer.infrastructure_container.get_cluster_status_use_case]),
) -> ClusterStatusResponse:
    """
    Kafka 클러스터 상태 조회

    Returns:
        클러스터 상태 (브로커 목록, 토픽/파티션 수)
    """
    cluster_status = await use_case.execute()

    # msgspec.Struct를 Pydantic 모델로 변환
    return ClusterStatusResponse(
        cluster_id=cluster_status.cluster_id,
        controller_id=cluster_status.controller_id,
        brokers=[
            BrokerResponse(
                broker_id=broker.broker_id,
                host=broker.host,
                port=broker.port,
                is_controller=broker.is_controller,
                leader_partition_count=broker.leader_partition_count,
            )
            for broker in cluster_status.brokers
        ],
        total_topics=cluster_status.total_topics,
        total_partitions=cluster_status.total_partitions,
    )
