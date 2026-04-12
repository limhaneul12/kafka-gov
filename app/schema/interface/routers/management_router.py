from dataclasses import asdict
from typing import Annotated

from dependency_injector.wiring import Provide, inject
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)

from app.container import AppContainer
from app.schema.domain.models import (
    DomainCompatibilityMode,
    DomainEnvironment,
    DomainSubjectStrategy,
)
from app.schema.interface.schemas import (
    SchemaArtifact,
    SchemaDeleteImpactResponse,
    SchemaSyncResponse,
    SchemaUploadResponse,
)
from app.schema.interface.schemas.search import SchemaSearchItem, SchemaSearchResponse
from app.schema.interface.types.enums import CompatibilityMode, Environment
from app.schema.interface.types.type_hints import ChangeId
from app.shared.actor import actor_context_dict, actor_context_from_headers
from app.shared.error_handlers import handle_api_errors, handle_server_errors

router = APIRouter(prefix="/v1/schemas", tags=["schema-management"])


def _resolve_actor(request: Request) -> tuple[str, dict[str, str] | None]:
    actor_context = actor_context_from_headers(request.headers)
    return actor_context.actor, actor_context_dict(actor_context)


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
    request: Request,
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
    actor, actor_context = _resolve_actor(request)

    result = await upload_use_case.execute(
        registry_id=registry_id,
        storage_id=storage_id,
        env=DomainEnvironment(env.value),
        change_id=change_id,
        owner=owner,
        files=files,
        actor=actor,
        compatibility_mode=domain_compatibility,
        strategy_id=strategy_id,
        actor_context=actor_context,
    )

    # 도메인 객체를 Pydantic 응답으로 변환
    return SchemaUploadResponse(
        upload_id=result.upload_id,
        artifacts=[
            SchemaArtifact(
                subject=artifact.subject,
                version=artifact.version,
                storage_url=artifact.storage_url,
                checksum=artifact.checksum,
            )
            for artifact in result.artifacts
        ],
        summary=result.summary(),
    )


@router.post(
    "/delete/analyze",
    response_model=SchemaDeleteImpactResponse,
    status_code=status.HTTP_200_OK,
    summary="스키마 삭제 사전 점검 (멀티 레지스트리)",
    description="스키마 삭제 전 버전/환경 경고와 naming-derived topic-name hints를 점검합니다. 실제 삭제는 수행하지 않습니다.",
)
@inject
@handle_api_errors(validation_error_message="Validation error")
async def analyze_schema_delete_impact(
    subject: str,
    request: Request,
    registry_id: str = Query(..., description="Schema Registry ID"),
    strategy: str = "TopicNameStrategy",
    delete_use_case=Depends(Provide[AppContainer.schema_container.delete_use_case]),
) -> SchemaDeleteImpactResponse:
    """스키마 삭제 영향도 분석"""
    # 영향도 분석 수행
    strategy_enum = DomainSubjectStrategy(strategy)
    actor, actor_context = _resolve_actor(request)
    impact = await delete_use_case.analyze(
        registry_id=registry_id,
        subject=subject,
        strategy=strategy_enum,
        actor=actor,
        actor_context=actor_context,
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
    description="스키마를 삭제합니다. 버전/환경 경고가 있으면 실패하며, naming-derived topic-name hints는 참고용으로만 반환합니다.",
)
@inject
@handle_api_errors(
    validation_error_message="Delete not safe",
    validation_status_code=status.HTTP_400_BAD_REQUEST,
)
async def delete_schema(
    subject: str,
    request: Request,
    registry_id: str = Query(..., description="Schema Registry ID"),
    strategy: str = "TopicNameStrategy",
    force: bool = False,
    delete_use_case=Depends(Provide[AppContainer.schema_container.delete_use_case]),
) -> SchemaDeleteImpactResponse:
    """스키마 삭제"""
    # 삭제 실행
    strategy_enum = DomainSubjectStrategy(strategy)
    actor, actor_context = _resolve_actor(request)
    impact = await delete_use_case.delete(
        registry_id=registry_id,
        subject=subject,
        strategy=strategy_enum,
        actor=actor,
        force=force,
        actor_context=actor_context,
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
    request: Request,
    registry_id: str = Query(..., description="Schema Registry ID"),
    sync_use_case=Depends(Provide[AppContainer.schema_container.sync_use_case]),
) -> SchemaSyncResponse:
    """Schema Registry → DB 동기화"""
    actor, actor_context = _resolve_actor(request)
    result = await sync_use_case.execute(
        registry_id=registry_id,
        actor=actor,
        actor_context=actor_context,
    )
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
    detail_use_case=Depends(Provide[AppContainer.schema_container.subject_detail_use_case]),
) -> dict[str, object]:
    """스키마 상세 조회"""
    detail = await detail_use_case.execute(registry_id=registry_id, subject=subject)
    return asdict(detail)


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
        SchemaSearchItem(
            subject=item.subject,
            version=item.version if item.version is not None else 1,
            storage_url=item.storage_url,
            checksum=item.checksum,
            schema_type=item.schema_type.value if item.schema_type else None,
            compatibility_mode=item.compatibility_mode.value if item.compatibility_mode else None,
            owner=item.owner,
            created_at=item.created_at.isoformat() if item.created_at else None,
        )
        for item in result.items
    ]

    return SchemaSearchResponse(
        items=items,
        total=result.total,
        page=page,
        limit=limit,
    )
