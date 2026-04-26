from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app.container import AppContainer
from app.schema.governance_support.actor import actor_context_dict, actor_context_from_headers
from app.schema.interface.adapters import (
    safe_convert_apply_result_to_response,
    safe_convert_plan_to_response,
    safe_convert_request_to_batch,
)
from app.schema.interface.schemas import (
    SchemaBatchApplyResponse,
    SchemaBatchDryRunResponse,
    SchemaBatchRequest,
)
from app.schema.interface.types.type_hints import ChangeId
from app.shared.error_handlers import handle_api_errors, handle_server_errors

router = APIRouter(prefix="/v1/schemas", tags=["schema-batch"])


def _resolve_actor(request: Request) -> tuple[str, dict[str, str] | None]:
    actor_context = actor_context_from_headers(request.headers)
    return actor_context.actor, actor_context_dict(actor_context)


@router.post(
    "/batch/dry-run",
    response_model=SchemaBatchDryRunResponse,
    status_code=status.HTTP_200_OK,
    summary="스키마 배치 Dry-Run (멀티 레지스트리)",
    description="스키마 배치 변경 계획을 생성하고 정책 및 호환성을 검증합니다.",
)
@inject
@handle_api_errors(validation_error_message="Validation error")
async def schema_batch_dry_run(
    request: SchemaBatchRequest,
    http_request: Request,
    registry_id: str = Query(..., description="Schema Registry ID"),
    dry_run_use_case=Depends(Provide[AppContainer.schema_container.dry_run_use_case]),
) -> SchemaBatchDryRunResponse:
    """스키마 배치 Dry-Run 실행"""
    batch = safe_convert_request_to_batch(request)
    actor, actor_context = _resolve_actor(http_request)
    plan = await dry_run_use_case.execute(registry_id, batch, actor, actor_context)
    return safe_convert_plan_to_response(plan)


@router.post(
    "/batch/apply",
    response_model=SchemaBatchApplyResponse,
    status_code=status.HTTP_200_OK,
    summary="스키마 배치 Apply (멀티 레지스트리/스토리지)",
    description="Dry-run 결과를 승인하여 스키마를 실제로 등록하고 아티팩트를 저장합니다.",
)
@inject
@handle_api_errors(validation_error_message="Policy violation")
async def schema_batch_apply(
    request: SchemaBatchRequest,
    http_request: Request,
    registry_id: str = Query(..., description="Schema Registry ID"),
    storage_id: str | None = Query(None, description="Object Storage ID (optional)"),
    apply_use_case=Depends(Provide[AppContainer.schema_container.apply_use_case]),
) -> SchemaBatchApplyResponse:
    """스키마 배치 Apply 실행"""
    batch = safe_convert_request_to_batch(request)
    actor, actor_context = _resolve_actor(http_request)
    result = await apply_use_case.execute(
        registry_id,
        storage_id,
        batch,
        actor,
        request.approval_override,
        actor_context,
    )
    return safe_convert_apply_result_to_response(result)


@router.get(
    "/plan/{change_id}",
    response_model=SchemaBatchDryRunResponse,
    status_code=status.HTTP_200_OK,
    summary="스키마 배치 계획 조회",
    description="저장된 스키마 배치 계획(dry-run 결과) 정보를 조회합니다.",
)
@inject
@handle_server_errors(error_message="Failed to retrieve plan")
async def get_schema_plan(
    change_id: ChangeId,
    plan_use_case=Depends(Provide[AppContainer.schema_container.plan_use_case]),
) -> SchemaBatchDryRunResponse:
    """스키마 배치 계획 조회"""
    result = await plan_use_case.execute(change_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plan '{change_id}' not found",
        )
    return safe_convert_plan_to_response(result)
