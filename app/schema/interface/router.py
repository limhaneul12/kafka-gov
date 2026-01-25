from dataclasses import asdict
from typing import Annotated

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status

from app.container import AppContainer
from app.schema.domain.models import (
    DomainCompatibilityMode,
    DomainEnvironment,
    DomainSubjectStrategy,
)
from app.schema.interface.adapters import (
    safe_convert_apply_result_to_response,
    safe_convert_plan_to_response,
    safe_convert_request_to_batch,
)
from app.schema.interface.schemas import (
    DashboardResponse,
    ImpactGraphResponse,
    RollbackRequest,
    SchemaBatchApplyResponse,
    SchemaBatchDryRunResponse,
    SchemaBatchRequest,
    SchemaChangeRequest,
    SchemaDeleteImpactResponse,
    SchemaHistoryResponse,
    SchemaSyncResponse,
    SchemaUploadResponse,
)
from app.schema.interface.schemas.search import SchemaSearchResponse
from app.schema.interface.types.enums import CompatibilityMode, Environment
from app.schema.interface.types.type_hints import ChangeId
from app.shared.error_handlers import handle_api_errors, handle_server_errors
from app.shared.roles import DEFAULT_USER

router = APIRouter(prefix="/v1/schemas", tags=["schemas"])


def _extract_schema_type_from_url(storage_url: str | None) -> str:
    """Storage URL에서 스키마 타입 추출"""
    if not storage_url:
        return "UNKNOWN"
    url_lower = storage_url.lower()
    if ".avsc" in url_lower or "/avro/" in url_lower:
        return "AVRO"
    elif ".proto" in url_lower or "/protobuf/" in url_lower:
        return "PROTOBUF"
    elif ".json" in url_lower or "/json/" in url_lower:
        return "JSON"
    return "UNKNOWN"


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
    registry_id: str = Query(..., description="Schema Registry ID"),
    dry_run_use_case=Depends(Provide[AppContainer.schema_container.dry_run_use_case]),
) -> SchemaBatchDryRunResponse:
    """스키마 배치 Dry-Run 실행"""
    batch = safe_convert_request_to_batch(request)
    plan = await dry_run_use_case.execute(registry_id, batch, DEFAULT_USER)
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
    registry_id: str = Query(..., description="Schema Registry ID"),
    storage_id: str | None = Query(None, description="Object Storage ID (optional)"),
    apply_use_case=Depends(Provide[AppContainer.schema_container.apply_use_case]),
) -> SchemaBatchApplyResponse:
    """스키마 배치 Apply 실행"""
    batch = safe_convert_request_to_batch(request)
    result = await apply_use_case.execute(registry_id, storage_id, batch, DEFAULT_USER)
    return safe_convert_apply_result_to_response(result)


@router.post(
    "/upload",
    response_model=SchemaUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="스키마 번들 업로드 (멀티 레지스트리/스토리지)",
    description="스키마 파일(.avsc/.proto/.json 및 zip 번들)을 업로드하여 사전 검증합니다.",
)
@inject
@handle_api_errors(validation_error_message="Validation error")
async def upload_schemas(
    env: Annotated[Environment, Form(..., description="업로드 대상 환경")],
    change_id: Annotated[ChangeId, Form(..., description="변경 ID")],
    owner: Annotated[str, Form(..., description="소유 팀")],
    files: Annotated[list[UploadFile], File(..., description="업로드할 스키마 파일 목록")],
    registry_id: Annotated[
        str, Query(description="Schema Registry ID (기본값: default)")
    ] = "default",
    storage_id: Annotated[str | None, Query(description="Object Storage ID (optional)")] = None,
    compatibility_mode: Annotated[
        CompatibilityMode | None,
        Form(description="호환성 모드 (기본값: BACKWARD)"),
    ] = None,
    strategy_id: Annotated[
        str, Form(description="Subject naming strategy (기본값: gov:EnvPrefixed)")
    ] = "gov:EnvPrefixed",
    upload_use_case=Depends(Provide[AppContainer.schema_container.upload_use_case]),
) -> SchemaUploadResponse:
    """스키마 파일 업로드"""
    if not files:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="at least one file must be provided",
        )

    # 호환성 모드 변환 (Interface Enum -> Domain Enum)
    domain_compatibility = (
        DomainCompatibilityMode(compatibility_mode.value) if compatibility_mode else None
    )

    result = await upload_use_case.execute(
        registry_id=registry_id,
        storage_id=storage_id,
        env=DomainEnvironment(env.value),
        change_id=change_id,
        owner=owner,
        files=files,
        actor=DEFAULT_USER,
        compatibility_mode=domain_compatibility,
        strategy_id=strategy_id,
    )

    # 도메인 객체를 Pydantic 응답으로 변환
    return SchemaUploadResponse(
        upload_id=result.upload_id,
        artifacts=[
            {
                "subject": artifact.subject,
                "version": artifact.version,
                "storage_url": artifact.storage_url,
                "checksum": artifact.checksum,
            }
            for artifact in result.artifacts
        ],
        summary=result.summary(),
    )


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


@router.post(
    "/delete/analyze",
    response_model=SchemaDeleteImpactResponse,
    status_code=status.HTTP_200_OK,
    summary="스키마 삭제 영향도 분석 (멀티 레지스트리)",
    description="스키마 삭제 전 영향도를 분석합니다. 실제 삭제는 수행하지 않습니다.",
)
@inject
@handle_api_errors(validation_error_message="Validation error")
async def analyze_schema_delete_impact(
    subject: str,
    registry_id: str = Query(..., description="Schema Registry ID"),
    strategy: str = "TopicNameStrategy",
    delete_use_case=Depends(Provide[AppContainer.schema_container.delete_use_case]),
) -> SchemaDeleteImpactResponse:
    """스키마 삭제 영향도 분석"""
    # 영향도 분석 수행
    strategy_enum = DomainSubjectStrategy(strategy)
    impact = await delete_use_case.analyze(
        registry_id=registry_id,
        subject=subject,
        strategy=strategy_enum,
        actor=DEFAULT_USER,
    )

    # 응답 변환
    return SchemaDeleteImpactResponse(
        subject=impact.subject,
        current_version=impact.current_version,
        total_versions=impact.total_versions,
        affected_topics=list(impact.affected_topics),
        warnings=list(impact.warnings),
        safe_to_delete=impact.safe_to_delete,
    )


@router.delete(
    "/delete/{subject}",
    response_model=SchemaDeleteImpactResponse,
    status_code=status.HTTP_200_OK,
    summary="스키마 삭제 (멀티 레지스트리)",
    description="스키마를 삭제합니다. 영향도 분석 후 안전하지 않으면 실패합니다.",
)
@inject
@handle_api_errors(
    validation_error_message="Delete not safe",
    validation_status_code=status.HTTP_400_BAD_REQUEST,
)
async def delete_schema(
    subject: str,
    registry_id: str = Query(..., description="Schema Registry ID"),
    strategy: str = "TopicNameStrategy",
    force: bool = False,
    delete_use_case=Depends(Provide[AppContainer.schema_container.delete_use_case]),
) -> SchemaDeleteImpactResponse:
    """스키마 삭제"""
    # 삭제 실행
    strategy_enum = DomainSubjectStrategy(strategy)
    impact = await delete_use_case.delete(
        registry_id=registry_id,
        subject=subject,
        strategy=strategy_enum,
        actor=DEFAULT_USER,
        force=force,
    )

    # 응답 변환
    return SchemaDeleteImpactResponse(
        subject=impact.subject,
        current_version=impact.current_version,
        total_versions=impact.total_versions,
        affected_topics=list(impact.affected_topics),
        warnings=list(impact.warnings),
        safe_to_delete=impact.safe_to_delete,
    )


@router.get(
    "/artifacts",
    status_code=status.HTTP_200_OK,
    summary="등록된 스키마 아티팩트 목록 조회",
    description="MinIO에 저장된 모든 스키마 아티팩트 목록을 조회합니다.",
)
@inject
@handle_server_errors(error_message="Failed to list artifacts")
async def list_schema_artifacts(
    metadata_repository=Depends(Provide[AppContainer.schema_container.metadata_repository]),
) -> list[dict[str, str | int | None]]:
    """스키마 아티팩트 목록 조회"""
    # Repository에서 도메인 모델 조회 (호환성 모드 포함)
    artifacts = await metadata_repository.list_artifacts()

    # 도메인 모델 -> API 응답 변환
    return [
        {
            "subject": artifact.subject,
            "version": artifact.version,
            "storage_url": artifact.storage_url,
            "checksum": artifact.checksum,
            "schema_type": _extract_schema_type_from_url(artifact.storage_url),
            "compatibility_mode": artifact.compatibility_mode.value
            if artifact.compatibility_mode
            else None,
            "owner": artifact.owner,
        }
        for artifact in artifacts
    ]


@router.post(
    "/sync",
    status_code=status.HTTP_200_OK,
    summary="스키마 동기화 (멀티 레지스트리)",
    description="Schema Registry의 모든 스키마를 DB로 동기화합니다.",
)
@inject
@handle_server_errors(error_message="Schema sync failed")
async def sync_schemas(
    registry_id: str = Query(..., description="Schema Registry ID"),
    sync_use_case=Depends(Provide[AppContainer.schema_container.sync_use_case]),
) -> SchemaSyncResponse:
    """Schema Registry → DB 동기화"""
    result = await sync_use_case.execute(registry_id=registry_id, actor=DEFAULT_USER)
    return SchemaSyncResponse.model_validate(result)


@router.get(
    "/detail/{subject}",
    status_code=status.HTTP_200_OK,
    summary="스키마 상세 단건 조회",
    description="특정 Subject의 최신 버전 스키마와 메타데이터를 통합하여 조회합니다.",
)
@inject
@handle_server_errors(error_message="Failed to load schema detail")
async def get_schema_detail(
    subject: str,
    registry_id: str = Query(..., description="Schema Registry ID"),
    governance_use_case=Depends(Provide[AppContainer.schema_container.governance_use_case]),
) -> dict:
    """스키마 상세 조회"""
    detail = await governance_use_case.get_subject_detail(registry_id=registry_id, subject=subject)
    return asdict(detail)


# -----------------------------------------------------------------------------
# Governance Dashboard APIs
# -----------------------------------------------------------------------------


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
    governance_use_case=Depends(Provide[AppContainer.schema_container.governance_use_case]),
) -> DashboardResponse:
    """거버넌스 대시보드 조회"""
    stats = await governance_use_case.get_dashboard_stats(registry_id=registry_id)
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
    governance_use_case=Depends(Provide[AppContainer.schema_container.governance_use_case]),
) -> SchemaHistoryResponse:
    """스키마 이력 조회"""
    history = await governance_use_case.get_history(registry_id=registry_id, subject=subject)
    return SchemaHistoryResponse.model_validate(asdict(history))


@router.get(
    "/impact/{subject}",
    response_model=ImpactGraphResponse,
    status_code=status.HTTP_200_OK,
    summary="영향도 그래프 (Lineage)",
    description="스키마(Subject) -> 토픽 -> 컨슈머로 이어지는 의존 관계를 그래프 데이터로 반환합니다.",
)
@inject
@handle_server_errors(error_message="Failed to load impact graph")
async def get_impact_graph(
    subject: str,
    registry_id: str = Query(..., description="Schema Registry ID"),
    governance_use_case=Depends(Provide[AppContainer.schema_container.governance_use_case]),
) -> ImpactGraphResponse:
    """스키마 영향도 그래프 조회"""
    graph = await governance_use_case.get_impact_graph(registry_id=registry_id, subject=subject)
    return ImpactGraphResponse.model_validate(asdict(graph))


@router.get(
    "/search",
    response_model=SchemaSearchResponse,
    status_code=status.HTTP_200_OK,
    summary="스키마 검색 (필터링 & 페이지네이션)",
    description="메타데이터(Subject, Owner)를 기반으로 스키마를 검색합니다.",
)
@inject
@handle_server_errors(error_message="Failed to search schemas")
async def search_schemas(
    query: str | None = Query(None, description="검색어 (Subject 포함)"),
    owner: str | None = Query(None, description="소유자 (Owner) 일치 검색"),
    page: int = Query(1, ge=1, description="페이지 번호"),
    limit: int = Query(20, ge=1, le=100, description="페이지 당 항목 수"),
    search_use_case=Depends(Provide[AppContainer.schema_container.search_use_case]),
) -> SchemaSearchResponse:
    """스키마 검색"""
    result = await search_use_case.execute(query=query, owner=owner, page=page, limit=limit)

    # DomainSchemaArtifact -> SchemaArtifactResponse 변환
    items = [
        {
            "subject": item.subject,
            "version": item.version,
            "storage_url": item.storage_url,
            "checksum": item.checksum,
            "schema_type": item.schema_type.value if item.schema_type else None,
            "compatibility_mode": item.compatibility_mode.value
            if item.compatibility_mode
            else None,
            "owner": item.owner,
            "created_at": item.created_at.isoformat() if item.created_at else None,
        }
        for item in result.items
    ]

    return SchemaSearchResponse(
        items=items,
        total=result.total,
        page=page,
        limit=limit,
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
    registry_id: str = Query(..., description="Schema Registry ID"),
    governance_use_case=Depends(Provide[AppContainer.schema_container.governance_use_case]),
) -> SchemaBatchDryRunResponse:
    """단건 스키마 변경 계획 수립"""
    plan = await governance_use_case.plan_change(
        registry_id=registry_id,
        subject=request.subject,
        new_schema=request.new_schema,
        compatibility=request.compatibility
        if isinstance(request.compatibility, str)
        else request.compatibility.value,
        actor=DEFAULT_USER,
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
    registry_id: str = Query(..., description="Schema Registry ID"),
    governance_use_case=Depends(Provide[AppContainer.schema_container.governance_use_case]),
) -> SchemaBatchDryRunResponse:
    """스키마 롤백 계획 수립"""
    plan = await governance_use_case.rollback(
        registry_id=registry_id,
        subject=request.subject,
        version=request.version,
        actor=DEFAULT_USER,
    )
    return safe_convert_plan_to_response(plan)
