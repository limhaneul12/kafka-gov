"""Schema 모듈 라우터 - 단순하고 실용적인 구현"""

from typing import Annotated

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.container import AppContainer
from app.schema.domain.models import DomainEnvironment, DomainSubjectStrategy
from app.schema.interface.adapters import (
    safe_convert_apply_result_to_response,
    safe_convert_plan_to_response,
    safe_convert_request_to_batch,
)
from app.schema.interface.schema import (
    SchemaBatchApplyResponse,
    SchemaBatchDryRunResponse,
    SchemaBatchRequest,
    SchemaDeleteImpactResponse,
    SchemaUploadResponse,
)
from app.schema.interface.types.enums import Environment
from app.schema.interface.types.type_hints import ChangeId
from app.shared.roles import DEFAULT_USER

router = APIRouter(prefix="/v1/schemas", tags=["schemas"])

# =============================================================================
# Dependency Injection - @inject 데코레이터로 엔드포인트에 직접 주입
# =============================================================================
DryRunUseCase = Depends(Provide[AppContainer.schema_container.dry_run_use_case])
ApplyUseCase = Depends(Provide[AppContainer.schema_container.apply_use_case])
UploadUseCase = Depends(Provide[AppContainer.schema_container.upload_use_case])
PlanUseCase = Depends(Provide[AppContainer.schema_container.plan_use_case])
DeleteAnalysisUseCase = Depends(Provide[AppContainer.schema_container.delete_analysis_use_case])
DeleteUseCase = Depends(Provide[AppContainer.schema_container.delete_use_case])
SyncUseCase = Depends(Provide[AppContainer.schema_container.sync_use_case])
MetadataRepository = Depends(Provide[AppContainer.schema_container.metadata_repository])


def _extract_schema_type_from_url(storage_url: str) -> str:
    """Storage URL에서 스키마 타입 추출"""
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
    summary="스키마 배치 Dry-Run",
    description="스키마 배치 변경 계획을 생성하고 정책 및 호환성을 검증합니다.",
)
@inject
async def schema_batch_dry_run(
    request: SchemaBatchRequest,
    dry_run_use_case=DryRunUseCase,
) -> SchemaBatchDryRunResponse:
    """스키마 배치 Dry-Run 실행"""
    try:
        batch = safe_convert_request_to_batch(request)
        plan = await dry_run_use_case.execute(batch, DEFAULT_USER)
        return safe_convert_plan_to_response(plan)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Validation error: {exc!s}",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {exc!s}",
        ) from exc


@router.post(
    "/batch/apply",
    response_model=SchemaBatchApplyResponse,
    status_code=status.HTTP_200_OK,
    summary="스키마 배치 Apply",
    description="Dry-run 결과를 승인하여 스키마를 실제로 등록하고 아티팩트를 저장합니다.",
)
@inject
async def schema_batch_apply(
    request: SchemaBatchRequest,
    apply_use_case=ApplyUseCase,
) -> SchemaBatchApplyResponse:
    """스키마 배치 Apply 실행"""
    try:
        batch = safe_convert_request_to_batch(request)
        result = await apply_use_case.execute(batch, DEFAULT_USER)
        return safe_convert_apply_result_to_response(result)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Policy violation: {exc!s}",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {exc!s}",
        ) from exc


@router.post(
    "/upload",
    response_model=SchemaUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="스키마 번들 업로드",
    description="스키마 파일(.avsc/.proto/.json 및 zip 번들)을 업로드하여 사전 검증합니다.",
)
@inject
async def upload_schemas(
    env: Annotated[Environment, Form(..., description="업로드 대상 환경")],
    change_id: Annotated[ChangeId, Form(..., description="변경 ID")],
    files: Annotated[list[UploadFile], File(..., description="업로드할 스키마 파일 목록")],
    upload_use_case=UploadUseCase,
) -> SchemaUploadResponse:
    """스키마 파일 업로드"""
    if not files:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="at least one file must be provided",
        )

    try:
        result = await upload_use_case.execute(
            env=DomainEnvironment(env.value),
            change_id=change_id,
            files=files,
            actor=DEFAULT_USER,
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
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Validation error: {exc!s}",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {exc!s}",
        ) from exc


@router.get(
    "/plan/{change_id}",
    response_model=SchemaBatchDryRunResponse,
    status_code=status.HTTP_200_OK,
    summary="스키마 배치 계획 조회",
    description="저장된 스키마 배치 계획(dry-run 결과) 정보를 조회합니다.",
)
@inject
async def get_schema_plan(
    change_id: ChangeId,
    plan_use_case=PlanUseCase,
) -> SchemaBatchDryRunResponse:
    """스키마 배치 계획 조회"""
    try:
        result = await plan_use_case.execute(change_id)
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Plan '{change_id}' not found",
            )
        return safe_convert_plan_to_response(result)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {exc!s}",
        ) from exc


@router.post(
    "/delete/analyze",
    response_model=SchemaDeleteImpactResponse,
    status_code=status.HTTP_200_OK,
    summary="스키마 삭제 영향도 분석",
    description="스키마 삭제 전 영향도를 분석합니다. 실제 삭제는 수행하지 않습니다.",
)
@inject
async def analyze_schema_delete_impact(
    subject: str,
    strategy: str = "TopicNameStrategy",
    delete_analysis_use_case=DeleteAnalysisUseCase,
) -> SchemaDeleteImpactResponse:
    """스키마 삭제 영향도 분석"""
    try:
        # 영향도 분석 수행
        strategy_enum = DomainSubjectStrategy(strategy)
        impact = await delete_analysis_use_case.analyze(
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

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Validation error: {exc!s}",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {exc!s}",
        ) from exc


@router.delete(
    "/delete/{subject}",
    response_model=SchemaDeleteImpactResponse,
    status_code=status.HTTP_200_OK,
    summary="스키마 삭제",
    description="스키마를 삭제합니다. 영향도 분석 후 안전하지 않으면 실패합니다.",
)
@inject
async def delete_schema(
    subject: str,
    strategy: str = "TopicNameStrategy",
    force: bool = False,
    delete_use_case=DeleteUseCase,
) -> SchemaDeleteImpactResponse:
    """스키마 삭제"""
    try:
        # 삭제 실행
        strategy_enum = DomainSubjectStrategy(strategy)
        impact = await delete_use_case.delete(
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

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Delete not safe: {exc!s}",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {exc!s}",
        ) from exc


@router.get(
    "/artifacts",
    status_code=status.HTTP_200_OK,
    summary="등록된 스키마 아티팩트 목록 조회",
    description="MinIO에 저장된 모든 스키마 아티팩트 목록을 조회합니다.",
)
@inject
async def list_schema_artifacts(
    metadata_repository=MetadataRepository,
) -> list[dict[str, str | int]]:
    """스키마 아티팩트 목록 조회"""
    try:
        # Repository를 통해 조회
        artifacts = await metadata_repository.list_artifacts()

        # 도메인 객체를 API 응답으로 변환 (스키마 타입 추출)
        return [
            {
                "subject": artifact.subject,
                "version": artifact.version,
                "storage_url": artifact.storage_url,
                "checksum": artifact.checksum,
                "schema_type": _extract_schema_type_from_url(artifact.storage_url),
            }
            for artifact in artifacts
        ]
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {exc!s}",
        ) from exc


@router.post(
    "/sync",
    status_code=status.HTTP_200_OK,
    summary="스키마 동기화",
    description="Schema Registry의 모든 스키마를 DB로 동기화합니다.",
)
@inject
async def sync_schemas(
    sync_use_case=SyncUseCase,
) -> dict[str, int]:
    """Schema Registry → DB 동기화"""
    try:
        result = await sync_use_case.execute(actor=DEFAULT_USER)
        return result
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Schema sync failed: {exc!s}",
        ) from exc
