"""Schema 모듈 라우터 - 단순하고 실용적인 구현"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import JSONResponse

from ...shared import auth as shared_auth
from ..application.use_cases import (
    SchemaBatchApplyUseCase,
    SchemaBatchDryRunUseCase,
    SchemaPlanUseCase,
    SchemaUploadUseCase,
)
from ..container import (
    DbSession,
    get_schema_apply_use_case,
    get_schema_dry_run_use_case,
    get_schema_plan_use_case,
    get_schema_upload_use_case,
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


def _get_current_user_dep(request: Request) -> str:
    """런타임에 shared_auth.get_current_user를 호출하는 얇은 래퍼.
    테스트에서 patch("app.shared.auth.get_current_user")가 효과를 발휘하도록 보장한다.
    """
    return shared_auth.get_current_user(request)


async def _get_dry_run_use_case_dep(session: DbSession) -> SchemaBatchDryRunUseCase:
    """DI 경계의 레이트 바인딩을 보장해 테스트·운영 모두에서 교체 용이성 확보"""
    return await get_schema_dry_run_use_case(session)


async def _get_apply_use_case_dep(session: DbSession) -> SchemaBatchApplyUseCase:
    """Apply 유스케이스 의존성 주입"""
    return await get_schema_apply_use_case(session)


async def _get_upload_use_case_dep(session: DbSession) -> SchemaUploadUseCase:
    """Upload 유스케이스 의존성 주입"""
    return await get_schema_upload_use_case(session)


def _get_plan_use_case_dep(session: DbSession) -> SchemaPlanUseCase:
    """Plan 유스케이스 의존성 주입"""
    return get_schema_plan_use_case(session)


@router.post(
    "/batch/dry-run",
    response_model=SchemaBatchDryRunResponse,
    status_code=status.HTTP_200_OK,
    summary="스키마 배치 Dry-Run",
    description="스키마 배치 변경 계획을 생성하고 정책 및 호환성을 검증합니다.",
)
async def schema_batch_dry_run(
    request: SchemaBatchRequest,
    dry_run_use_case: Annotated[SchemaBatchDryRunUseCase, Depends(_get_dry_run_use_case_dep)],
    current_user: Annotated[str, Depends(_get_current_user_dep)],
) -> SchemaBatchDryRunResponse:
    """스키마 배치 Dry-Run 실행"""
    try:
        batch = safe_convert_request_to_batch(request)
        plan = await dry_run_use_case.execute(batch, current_user)
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
async def schema_batch_apply(
    request: SchemaBatchRequest,
    apply_use_case: Annotated[SchemaBatchApplyUseCase, Depends(_get_apply_use_case_dep)],
    current_user: Annotated[str, Depends(_get_current_user_dep)],
) -> SchemaBatchApplyResponse:
    """스키마 배치 Apply 실행"""
    try:
        batch = safe_convert_request_to_batch(request)
        result = await apply_use_case.execute(batch, current_user)
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
async def upload_schemas(
    env: Annotated[Environment, Form(..., description="업로드 대상 환경")],
    change_id: Annotated[ChangeId, Form(..., description="변경 ID")],
    files: Annotated[list[UploadFile], File(..., description="업로드할 스키마 파일 목록")],
    upload_use_case: Annotated[SchemaUploadUseCase, Depends(_get_upload_use_case_dep)],
    current_user: Annotated[str, Depends(_get_current_user_dep)],
) -> SchemaUploadResponse:
    """스키마 파일 업로드"""
    if not files:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="at least one file must be provided",
        )

    try:
        # Environment 타입 변환
        from ..domain.models import DomainEnvironment

        domain_env = DomainEnvironment(env.value)

        result = await upload_use_case.execute(
            env=domain_env,
            change_id=change_id,
            files=files,
            actor=current_user,
        )
        return SchemaUploadResponse.model_validate(result)
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
async def get_schema_plan(
    change_id: ChangeId,
    plan_use_case: Annotated[SchemaPlanUseCase, Depends(_get_plan_use_case_dep)],
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
