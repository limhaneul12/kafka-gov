from dataclasses import asdict

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Query, Request, Response, status

from app.container import AppContainer
from app.schema.governance_support.actor import actor_context_dict, actor_context_from_headers
from app.schema.interface.adapters import (
    safe_convert_apply_result_to_response,
    safe_convert_plan_to_response,
)
from app.schema.interface.schemas import (
    DashboardResponse,
    RollbackExecuteRequest,
    RollbackRequest,
    SchemaBatchApplyResponse,
    SchemaBatchDryRunResponse,
    SchemaChangeRequest,
    SchemaDriftResponse,
    SchemaHistoryResponse,
    SchemaSettingsResponse,
    SchemaSettingsUpdateRequest,
    SchemaVersionCompareResponse,
    SchemaVersionDetailResponse,
    SchemaVersionListResponse,
)
from app.shared.error_handlers import (
    endpoint_error_handler,
    handle_api_errors,
    handle_server_errors,
)

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


@router.get(
    "/drift/{subject}",
    response_model=SchemaDriftResponse,
    status_code=status.HTTP_200_OK,
    summary="스키마 drift 보고서 조회",
    description="라이브 registry 최신 상태와 로컬 catalog snapshot 간 drift를 조회합니다.",
)
@inject
@endpoint_error_handler(
    error_mappings={ValueError: (status.HTTP_404_NOT_FOUND, "Schema subject not found")},
    default_message="Failed to load schema drift report",
)
async def get_schema_drift(
    subject: str,
    registry_id: str = Query(..., description="Schema Registry ID"),
    drift_use_case=Depends(Provide[AppContainer.schema_container.schema_drift_use_case]),
) -> SchemaDriftResponse:
    drift = await drift_use_case.execute(registry_id=registry_id, subject=subject)
    return SchemaDriftResponse.model_validate(asdict(drift))


@router.patch(
    "/settings/{subject}",
    response_model=SchemaSettingsResponse,
    status_code=status.HTTP_200_OK,
    summary="스키마 메타데이터/호환성 설정 업데이트",
)
@inject
@handle_api_errors(validation_error_message="Schema settings update failed")
async def update_schema_settings(
    subject: str,
    request: SchemaSettingsUpdateRequest,
    http_request: Request,
    registry_id: str = Query(..., description="Schema Registry ID"),
    settings_use_case=Depends(
        Provide[AppContainer.schema_container.update_schema_settings_use_case]
    ),
) -> SchemaSettingsResponse:
    actor, actor_context = _resolve_actor(http_request)
    result = await settings_use_case.execute(
        registry_id=registry_id,
        subject=subject,
        actor=actor,
        owner=request.owner,
        doc=request.doc,
        tags=request.tags,
        description=request.description,
        compatibility_mode=(
            request.compatibility_mode.value if request.compatibility_mode is not None else None
        ),
        actor_context=actor_context,
    )
    return SchemaSettingsResponse.model_validate(asdict(result))


@router.get(
    "/subjects/{subject}/versions",
    response_model=SchemaVersionListResponse,
    status_code=status.HTTP_200_OK,
    summary="스키마 버전 목록 조회",
    description="특정 Subject의 전체 버전 목록을 최신순으로 조회합니다.",
)
@inject
@endpoint_error_handler(
    error_mappings={ValueError: (status.HTTP_404_NOT_FOUND, "Schema subject not found")},
    default_message="Failed to load schema versions",
)
async def list_schema_versions(
    subject: str,
    registry_id: str = Query(..., description="Schema Registry ID"),
    versions_use_case=Depends(Provide[AppContainer.schema_container.schema_versions_use_case]),
) -> SchemaVersionListResponse:
    versions = await versions_use_case.execute(registry_id=registry_id, subject=subject)
    return SchemaVersionListResponse.model_validate(asdict(versions))


@router.get(
    "/subjects/{subject}/compare",
    response_model=SchemaVersionCompareResponse,
    status_code=status.HTTP_200_OK,
    summary="스키마 버전 비교",
    description="동일 subject의 두 버전을 비교하여 변경 요약과 원본 스키마를 반환합니다.",
)
@inject
@endpoint_error_handler(
    error_mappings={ValueError: (status.HTTP_404_NOT_FOUND, "Schema version not found")},
    default_message="Failed to compare schema versions",
)
async def compare_schema_versions(
    subject: str,
    from_version: int = Query(..., ge=1, description="기준 버전"),
    to_version: int = Query(..., ge=1, description="비교 대상 버전"),
    registry_id: str = Query(..., description="Schema Registry ID"),
    compare_use_case=Depends(
        Provide[AppContainer.schema_container.compare_schema_versions_use_case]
    ),
) -> SchemaVersionCompareResponse:
    comparison = await compare_use_case.execute(
        registry_id=registry_id,
        subject=subject,
        from_version=from_version,
        to_version=to_version,
    )
    return SchemaVersionCompareResponse.model_validate(asdict(comparison))


@router.get(
    "/subjects/{subject}/versions/{version}",
    response_model=SchemaVersionDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="특정 스키마 버전 상세 조회",
    description="특정 Subject의 정확한 버전 스키마와 메타데이터를 조회합니다.",
)
@inject
@endpoint_error_handler(
    error_mappings={ValueError: (status.HTTP_404_NOT_FOUND, "Schema version not found")},
    default_message="Failed to load schema version",
)
async def get_schema_version(
    subject: str,
    version: int,
    registry_id: str = Query(..., description="Schema Registry ID"),
    version_use_case=Depends(Provide[AppContainer.schema_container.schema_version_use_case]),
) -> SchemaVersionDetailResponse:
    detail = await version_use_case.execute(
        registry_id=registry_id,
        subject=subject,
        version=version,
    )
    return SchemaVersionDetailResponse.model_validate(asdict(detail))


@router.get(
    "/subjects/{subject}/versions/{version}/export",
    status_code=status.HTTP_200_OK,
    summary="특정 스키마 버전 export",
    description="특정 Subject 버전의 원본 스키마를 다운로드합니다.",
)
@inject
@endpoint_error_handler(
    error_mappings={ValueError: (status.HTTP_404_NOT_FOUND, "Schema version not found")},
    default_message="Failed to export schema version",
)
async def export_schema_version(
    subject: str,
    version: int,
    registry_id: str = Query(..., description="Schema Registry ID"),
    export_use_case=Depends(Provide[AppContainer.schema_container.export_schema_version_use_case]),
) -> Response:
    exported = await export_use_case.execute(
        registry_id=registry_id,
        subject=subject,
        version=version,
    )
    return Response(
        content=exported.schema_str,
        media_type=exported.media_type,
        headers={"Content-Disposition": f'attachment; filename="{exported.filename}"'},
    )


@router.get(
    "/subjects/{subject}/export",
    status_code=status.HTTP_200_OK,
    summary="최신 스키마 export",
    description="특정 Subject의 최신 스키마를 다운로드합니다.",
)
@inject
@endpoint_error_handler(
    error_mappings={ValueError: (status.HTTP_404_NOT_FOUND, "Schema subject not found")},
    default_message="Failed to export latest schema",
)
async def export_latest_schema(
    subject: str,
    registry_id: str = Query(..., description="Schema Registry ID"),
    export_use_case=Depends(Provide[AppContainer.schema_container.export_schema_version_use_case]),
) -> Response:
    exported = await export_use_case.execute_latest(
        registry_id=registry_id,
        subject=subject,
    )
    return Response(
        content=exported.schema_str,
        media_type=exported.media_type,
        headers={"Content-Disposition": f'attachment; filename="{exported.filename}"'},
    )


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


@router.post(
    "/rollback/execute",
    response_model=SchemaBatchApplyResponse,
    status_code=status.HTTP_200_OK,
    summary="스키마 롤백 실행",
    description="특정 버전의 스키마를 현재 subject의 새 버전으로 다시 등록합니다.",
)
@inject
@handle_api_errors(validation_error_message="Rollback execute failed")
async def execute_schema_rollback(
    request: RollbackExecuteRequest,
    http_request: Request,
    registry_id: str = Query(..., description="Schema Registry ID"),
    execute_rollback_use_case=Depends(
        Provide[AppContainer.schema_container.execute_rollback_use_case]
    ),
) -> SchemaBatchApplyResponse:
    actor, actor_context = _resolve_actor(http_request)
    result = await execute_rollback_use_case.execute(
        registry_id=registry_id,
        subject=request.subject,
        version=request.version,
        actor=actor,
        approval_override=request.approval_override,
        reason=request.reason,
        actor_context=actor_context,
    )
    return safe_convert_apply_result_to_response(result)
