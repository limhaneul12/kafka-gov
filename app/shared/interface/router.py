"""Shared Interface Router"""

from datetime import datetime
from typing import Any

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Query

from app.container import AppContainer
from app.shared.error_handlers import endpoint_error_handler
from app.shared.interface.schema import (
    ApprovalDecisionRequest,
    ApprovalRequestCreateRequest,
    ApprovalRequestResponse,
    BrokerResponse,
    ClusterStatusResponse,
)

router = APIRouter(prefix="/v1", tags=["shared"])

RecentActivitiesResponse = Depends(
    Provide[AppContainer.infrastructure_container.get_recent_activities_use_case]
)
ActivityHistoryResponse = Depends(
    Provide[AppContainer.infrastructure_container.get_activity_history_use_case]
)
ClusterStatus = Depends(Provide[AppContainer.infrastructure_container.get_cluster_status_use_case])
CreateApprovalRequest = Depends(
    Provide[AppContainer.infrastructure_container.create_approval_request_use_case]
)
ListApprovalRequests = Depends(
    Provide[AppContainer.infrastructure_container.list_approval_requests_use_case]
)
GetApprovalRequest = Depends(
    Provide[AppContainer.infrastructure_container.get_approval_request_use_case]
)
ApproveApprovalRequest = Depends(
    Provide[AppContainer.infrastructure_container.approve_approval_request_use_case]
)
RejectApprovalRequest = Depends(
    Provide[AppContainer.infrastructure_container.reject_approval_request_use_case]
)


@router.get("/audit/recent")
@inject
@endpoint_error_handler(default_message="Failed to retrieve recent activities")
async def get_recent_activities(
    use_case=RecentActivitiesResponse,
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

    # dataclass를 dict로 변환 (FastAPI 직렬화)
    result: list[dict[str, Any]] = [
        {
            "activity_type": activity.activity_type,
            "action": activity.action,
            "target": activity.target,
            "message": activity.message,
            "actor": activity.actor,
            "team": activity.team,
            "timestamp": activity.timestamp.isoformat(),
            "metadata": activity.metadata,
        }
        for activity in activities
    ]

    return result


@router.get("/audit/history")
@inject
@endpoint_error_handler(default_message="Failed to retrieve activity history")
async def get_activity_history(
    use_case=ActivityHistoryResponse,
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

    # dataclass를 dict로 변환
    result: list[dict[str, Any]] = [
        {
            "activity_type": activity.activity_type,
            "action": activity.action,
            "target": activity.target,
            "message": activity.message,
            "actor": activity.actor,
            "team": activity.team,
            "timestamp": activity.timestamp.isoformat(),
            "metadata": activity.metadata,
        }
        for activity in activities
    ]

    return result


@router.get("/cluster/status", response_model=ClusterStatusResponse)
@inject
@endpoint_error_handler(default_message="Failed to retrieve cluster status")
async def get_cluster_status(
    use_case=ClusterStatus,
    cluster_id: str = Query(..., description="클러스터 ID"),
) -> ClusterStatusResponse:
    """
    Kafka 클러스터 상태 조회

    Args:
        cluster_id: 클러스터 ID

    Returns:
        클러스터 상태 (브로커 목록, 토픽/파티션 수)
    """
    cluster_status = await use_case.execute(cluster_id=cluster_id)

    # dataclass를 Pydantic 모델로 변환
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


@router.post("/approval-requests", response_model=ApprovalRequestResponse)
@inject
@endpoint_error_handler(default_message="Failed to create approval request")
async def create_approval_request(
    request: ApprovalRequestCreateRequest,
    use_case=CreateApprovalRequest,
) -> ApprovalRequestResponse:
    created = await use_case.execute(
        resource_type=request.resource_type,
        resource_name=request.resource_name,
        change_type=request.change_type,
        change_ref=request.change_ref,
        summary=request.summary,
        justification=request.justification,
        requested_by=request.requested_by,
        metadata=request.metadata,
    )
    return ApprovalRequestResponse.model_validate(created)


@router.get("/approval-requests", response_model=list[ApprovalRequestResponse])
@inject
@endpoint_error_handler(default_message="Failed to list approval requests")
async def list_approval_requests(
    use_case=ListApprovalRequests,
    status: str | None = Query(default=None),
    resource_type: str | None = Query(default=None),
    requested_by: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[ApprovalRequestResponse]:
    requests = await use_case.execute(
        status=status,
        resource_type=resource_type,
        requested_by=requested_by,
        limit=limit,
    )
    return [ApprovalRequestResponse.model_validate(item) for item in requests]


@router.get("/approval-requests/{request_id}", response_model=ApprovalRequestResponse)
@inject
@endpoint_error_handler(default_message="Failed to retrieve approval request")
async def get_approval_request(
    request_id: str,
    use_case=GetApprovalRequest,
) -> ApprovalRequestResponse:
    request = await use_case.execute(request_id)
    return ApprovalRequestResponse.model_validate(request)


@router.post("/approval-requests/{request_id}/approve", response_model=ApprovalRequestResponse)
@inject
@endpoint_error_handler(default_message="Failed to approve approval request")
async def approve_approval_request(
    request_id: str,
    decision: ApprovalDecisionRequest,
    use_case=ApproveApprovalRequest,
) -> ApprovalRequestResponse:
    request = await use_case.execute(
        request_id=request_id,
        approver=decision.approver,
        decision_reason=decision.decision_reason,
    )
    return ApprovalRequestResponse.model_validate(request)


@router.post("/approval-requests/{request_id}/reject", response_model=ApprovalRequestResponse)
@inject
@endpoint_error_handler(default_message="Failed to reject approval request")
async def reject_approval_request(
    request_id: str,
    decision: ApprovalDecisionRequest,
    use_case=RejectApprovalRequest,
) -> ApprovalRequestResponse:
    request = await use_case.execute(
        request_id=request_id,
        approver=decision.approver,
        decision_reason=decision.decision_reason,
    )
    return ApprovalRequestResponse.model_validate(request)
