from dataclasses import asdict

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Query, Request, status

from app.container import AppContainer
from app.schema.interface.adapters import safe_convert_plan_to_response
from app.schema.interface.schemas import (
    DashboardResponse,
    RollbackRequest,
    SchemaBatchDryRunResponse,
    SchemaChangeRequest,
    SchemaHistoryResponse,
)
from app.shared.actor import actor_context_dict, actor_context_from_headers
from app.shared.error_handlers import handle_api_errors, handle_server_errors

router = APIRouter(prefix="/v1/schemas", tags=["schema-governance"])


def _resolve_actor(request: Request) -> tuple[str, dict[str, str] | None]:
    actor_context = actor_context_from_headers(request.headers)
    return actor_context.actor, actor_context_dict(actor_context)


@router.get(
    "/governance/dashboard",
    response_model=DashboardResponse,
    status_code=status.HTTP_200_OK,
    summary="거버넌스 대시보드 (통계 & 점수)",
    description="전체 스키마의 거버넌스 점수, 호환성 현황, 오너십 상태 등을 종합하여 보여줍니다.",
)
@inject
@handle_server_errors(error_message="Failed to load dashboard")
async def get_governance_dashboard(
    registry_id: str = Query(..., description="Schema Registry ID"),
    stats_use_case=Depends(Provide[AppContainer.schema_container.governance_stats_use_case]),
) -> DashboardResponse:
    stats = await stats_use_case.execute(registry_id=registry_id)
    return DashboardResponse.model_validate(asdict(stats))


@router.get(
    "/history/{subject}",
    response_model=SchemaHistoryResponse,
    status_code=status.HTTP_200_OK,
    summary="스키마 타임머신 (이력 조회)",
    description="특정 Subject의 모든 변경 이력을 시간 순으로 조회합니다.",
)
@inject
@handle_server_errors(error_message="Failed to load history")
async def get_schema_history(
    subject: str,
    registry_id: str = Query(..., description="Schema Registry ID"),
    history_use_case=Depends(Provide[AppContainer.schema_container.schema_history_use_case]),
) -> SchemaHistoryResponse:
    history = await history_use_case.execute(registry_id=registry_id, subject=subject)
    return SchemaHistoryResponse.model_validate(asdict(history))


@router.post(
    "/plan-change",
    response_model=SchemaBatchDryRunResponse,
    status_code=status.HTTP_200_OK,
    summary="단건 스키마 변경 계획 수립",
    description="편집된 스키마에 대해 변경 계획(Diff, 영향도)을 수립합니다.",
)
@inject
@handle_api_errors(validation_error_message="Plan failed")
async def plan_schema_change(
    request: SchemaChangeRequest,
    http_request: Request,
    registry_id: str = Query(..., description="Schema Registry ID"),
    plan_change_use_case=Depends(Provide[AppContainer.schema_container.plan_change_use_case]),
) -> SchemaBatchDryRunResponse:
    actor, actor_context = _resolve_actor(http_request)
    plan = await plan_change_use_case.execute(
        registry_id=registry_id,
        subject=request.subject,
        new_schema=request.new_schema,
        compatibility=request.compatibility
        if isinstance(request.compatibility, str)
        else request.compatibility.value,
        actor=actor,
        reason=request.reason,
        actor_context=actor_context,
    )
    return safe_convert_plan_to_response(plan)


@router.post(
    "/rollback/plan",
    response_model=SchemaBatchDryRunResponse,
    status_code=status.HTTP_200_OK,
    summary="스키마 롤백 계획 수립",
    description="특정 버전으로의 롤백 계획을 수립합니다.",
)
@inject
@handle_api_errors(validation_error_message="Rollback plan failed")
async def plan_schema_rollback(
    request: RollbackRequest,
    http_request: Request,
    registry_id: str = Query(..., description="Schema Registry ID"),
    rollback_use_case=Depends(Provide[AppContainer.schema_container.rollback_use_case]),
) -> SchemaBatchDryRunResponse:
    actor, actor_context = _resolve_actor(http_request)
    plan = await rollback_use_case.execute(
        registry_id=registry_id,
        subject=request.subject,
        version=request.version,
        actor=actor,
        reason=request.reason,
        actor_context=actor_context,
    )
    return safe_convert_plan_to_response(plan)
