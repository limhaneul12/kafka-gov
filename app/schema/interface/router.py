"""Schema FastAPI 라우터"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse

from ...shared.auth import get_current_user
from ..application.use_cases import (
    SchemaBatchApplyUseCase,
    SchemaBatchDryRunUseCase,
    SchemaPlanUseCase,
    SchemaUploadUseCase,
)
from ..container import (
    get_schema_apply_use_case,
    get_schema_dry_run_use_case,
    get_schema_plan_use_case,
    get_schema_upload_use_case,
)
from ..domain.models import (
    SchemaApplyResult as DomainSchemaApplyResult,
    SchemaPlan as DomainSchemaPlan,
)
from .adapters import (
    safe_convert_apply_result_to_response,
    safe_convert_plan_to_response,
    safe_convert_request_to_batch,
)
from .schema import (
    SchemaBatchApplyResponse,
    SchemaBatchDryRunResponse,
    SchemaBatchRequest,
    SchemaUploadResponse,
)
from .types.enums import Environment
from .types.type_hints import ChangeId

router = APIRouter(prefix="/v1/schemas", tags=["schemas"])


# TypeAdapter 기반 변환 함수는 adapters.py로 이동됨


# TypeAdapter 기반 변환 함수는 adapters.py로 이동됨


# TypeAdapter 기반 변환 함수는 adapters.py로 이동됨


@router.post(
    "/batch/dry-run",
    response_model=SchemaBatchDryRunResponse,
    status_code=status.HTTP_200_OK,
    summary="스키마 배치 Dry-Run",
    description="스키마 배치 변경 계획을 생성하고 정책 및 호환성을 검증합니다.",
)
async def schema_batch_dry_run(
    request: SchemaBatchRequest,
    dry_run_use_case: Annotated[SchemaBatchDryRunUseCase, Depends(get_schema_dry_run_use_case)],
    current_user: Annotated[str, Depends(get_current_user)],
) -> SchemaBatchDryRunResponse:
    """스키마 배치 Dry-Run 실행"""
    try:
        batch = safe_convert_request_to_batch(request)
        plan = await dry_run_use_case.execute(batch, current_user)
        if isinstance(plan, DomainSchemaPlan):
            return safe_convert_plan_to_response(plan)
        return SchemaBatchDryRunResponse.model_validate(plan)
    except NotImplementedError as exc:  # pragma: no cover - 초기 스텁 행동
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Validation error: {exc!s}",
        ) from exc
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - 예외 포착
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
async def schema_batch_apply(
    request: SchemaBatchRequest,
    apply_use_case: Annotated[SchemaBatchApplyUseCase, Depends(get_schema_apply_use_case)],
    current_user: Annotated[str, Depends(get_current_user)],
) -> SchemaBatchApplyResponse:
    """스키마 배치 Apply 실행"""
    try:
        batch = safe_convert_request_to_batch(request)
        result = await apply_use_case.execute(batch, current_user)
        if isinstance(result, DomainSchemaApplyResult):
            return safe_convert_apply_result_to_response(result)
        return SchemaBatchApplyResponse.model_validate(result)
    except NotImplementedError as exc:  # pragma: no cover - 초기 스텁 행동
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Policy violation: {exc!s}",
        ) from exc
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover
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
async def upload_schemas(
    env: Annotated[Environment, Form(..., description="업로드 대상 환경")],
    change_id: Annotated[ChangeId, Form(..., description="변경 ID")],
    files: Annotated[list[UploadFile], File(..., description="업로드할 스키마 파일 목록")],
    upload_use_case: Annotated[SchemaUploadUseCase, Depends(get_schema_upload_use_case)],
    current_user: Annotated[str, Depends(get_current_user)],
) -> SchemaUploadResponse:
    """스키마 파일 업로드"""
    if not files:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="at least one file must be provided",
        )

    try:
        result = await upload_use_case.execute(
            env=env,
            change_id=change_id,
            files=files,
            actor=current_user,
        )
        if isinstance(result, SchemaUploadResponse):
            return result
        return SchemaUploadResponse.model_validate(result)
    except NotImplementedError as exc:  # pragma: no cover - 초기 스텁 행동
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Validation error: {exc!s}",
        ) from exc
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover
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
async def get_schema_plan(
    change_id: ChangeId,
    plan_use_case: Annotated[SchemaPlanUseCase, Depends(get_schema_plan_use_case)],
) -> SchemaBatchDryRunResponse:
    """스키마 배치 계획 조회"""
    try:
        result = await plan_use_case.execute(change_id)
        if result is None:
            raise ValueError("plan not found")
        if isinstance(result, DomainSchemaPlan):
            return safe_convert_plan_to_response(result)
        return SchemaBatchDryRunResponse.model_validate(result)
    except NotImplementedError as exc:  # pragma: no cover
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plan '{change_id}' not found: {exc!s}",
        ) from exc
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {exc!s}",
        ) from exc


@router.get(
    "/health",
    status_code=status.HTTP_200_OK,
    summary="스키마 모듈 헬스체크",
    description="스키마 모듈의 기본 헬스 상태를 확인합니다.",
)
async def health_check() -> JSONResponse:
    """헬스체크"""
    return JSONResponse(
        content={
            "status": "healthy",
            "module": "schema",
            "version": "1.0.0",
        }
    )
