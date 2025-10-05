"""Shared Interface Router - 공통 API 엔드포인트"""

from __future__ import annotations

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
