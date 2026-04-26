from dataclasses import asdict
from datetime import datetime

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Body, Depends, Query, status

from app.container import AppContainer
from app.schema.interface.schemas import (
    ApprovalDecisionRequest,
    ApprovalRequestResponse,
    AuditActivityResponse,
)
from app.shared.error_handlers import endpoint_error_handler

router = APIRouter(prefix="/v1", tags=["schema-governance-operations"])


@router.get(
    "/approval-requests",
    response_model=list[ApprovalRequestResponse],
    status_code=status.HTTP_200_OK,
    summary="승인 요청 목록 조회",
)
@inject
@endpoint_error_handler(default_message="Failed to list approval requests")
async def list_approval_requests(
    status_filter: str | None = Query(None, alias="status"),
    resource_type: str | None = Query(None),
    requested_by: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    use_case=Depends(Provide[AppContainer.schema_container.list_approval_requests_use_case]),
) -> list[ApprovalRequestResponse]:
    requests = await use_case.execute(
        status=status_filter,
        resource_type=resource_type,
        requested_by=requested_by,
        limit=limit,
    )
    return [ApprovalRequestResponse.model_validate(asdict(item)) for item in requests]


@router.get(
    "/approval-requests/{request_id}",
    response_model=ApprovalRequestResponse,
    status_code=status.HTTP_200_OK,
    summary="승인 요청 상세 조회",
)
@inject
@endpoint_error_handler(
    error_mappings={ValueError: (status.HTTP_404_NOT_FOUND, "Approval request not found")},
    default_message="Failed to get approval request",
)
async def get_approval_request(
    request_id: str,
    use_case=Depends(Provide[AppContainer.schema_container.get_approval_request_use_case]),
) -> ApprovalRequestResponse:
    request = await use_case.execute(request_id)
    return ApprovalRequestResponse.model_validate(asdict(request))


@router.post(
    "/approval-requests/{request_id}/approve",
    response_model=ApprovalRequestResponse,
    status_code=status.HTTP_200_OK,
    summary="승인 요청 승인",
)
@inject
@endpoint_error_handler(
    error_mappings={ValueError: (status.HTTP_404_NOT_FOUND, "Approval request not found")},
    default_message="Failed to approve approval request",
)
async def approve_approval_request(
    request_id: str,
    payload: ApprovalDecisionRequest = Body(...),
    use_case=Depends(Provide[AppContainer.schema_container.approve_approval_request_use_case]),
) -> ApprovalRequestResponse:
    request = await use_case.execute(
        request_id=request_id,
        approver=payload.approver,
        decision_reason=payload.decision_reason,
    )
    return ApprovalRequestResponse.model_validate(asdict(request))


@router.post(
    "/approval-requests/{request_id}/reject",
    response_model=ApprovalRequestResponse,
    status_code=status.HTTP_200_OK,
    summary="승인 요청 반려",
)
@inject
@endpoint_error_handler(
    error_mappings={ValueError: (status.HTTP_404_NOT_FOUND, "Approval request not found")},
    default_message="Failed to reject approval request",
)
async def reject_approval_request(
    request_id: str,
    payload: ApprovalDecisionRequest = Body(...),
    use_case=Depends(Provide[AppContainer.schema_container.reject_approval_request_use_case]),
) -> ApprovalRequestResponse:
    request = await use_case.execute(
        request_id=request_id,
        approver=payload.approver,
        decision_reason=payload.decision_reason,
    )
    return ApprovalRequestResponse.model_validate(asdict(request))


@router.get(
    "/audit/recent",
    response_model=list[AuditActivityResponse],
    status_code=status.HTTP_200_OK,
    summary="최근 감사 활동 조회",
)
@inject
@endpoint_error_handler(default_message="Failed to load recent audit activities")
async def get_recent_audit_activities(
    limit: int = Query(20, ge=1, le=100),
    use_case=Depends(Provide[AppContainer.schema_container.recent_activities_use_case]),
) -> list[AuditActivityResponse]:
    activities = await use_case.execute(limit=limit)
    return [AuditActivityResponse.model_validate(asdict(item)) for item in activities]


@router.get(
    "/audit/history",
    response_model=list[AuditActivityResponse],
    status_code=status.HTTP_200_OK,
    summary="감사 활동 히스토리 조회",
)
@inject
@endpoint_error_handler(default_message="Failed to load audit history")
async def get_audit_history(
    from_date: datetime | None = Query(None),
    to_date: datetime | None = Query(None),
    activity_type: str | None = Query(None),
    action: str | None = Query(None),
    actor: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    use_case=Depends(Provide[AppContainer.schema_container.activity_history_use_case]),
) -> list[AuditActivityResponse]:
    activities = await use_case.execute(
        from_date=from_date,
        to_date=to_date,
        activity_type=activity_type,
        action=action,
        actor=actor,
        limit=limit,
    )
    return [AuditActivityResponse.model_validate(asdict(item)) for item in activities]
