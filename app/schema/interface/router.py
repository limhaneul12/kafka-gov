"""Schema 모듈 라우터 - 단순하고 실용적인 구현"""

from __future__ import annotations

from typing import Annotated, cast

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import ORJSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.schema.application.use_cases import (
    SchemaBatchApplyUseCase,
    SchemaBatchDryRunUseCase,
    SchemaDeleteAnalysisUseCase,
    SchemaPlanUseCase,
    SchemaUploadUseCase,
)
from app.schema.container import (
    DbSession,
    container,
    get_schema_apply_use_case,
    get_schema_dry_run_use_case,
    get_schema_plan_use_case,
    get_schema_upload_use_case,
)
from app.schema.domain.models import DomainEnvironment, DomainSubjectStrategy
from app.schema.domain.repositories.interfaces import ISchemaAuditRepository
from app.schema.infrastructure.repository.audit_repository import MySQLSchemaAuditRepository
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
from app.shared.database import get_db_session
from app.shared.roles import DEFAULT_USER

router = APIRouter(prefix="/v1/schemas", tags=["schemas"])


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
async def schema_batch_apply(
    request: SchemaBatchRequest,
    apply_use_case: Annotated[SchemaBatchApplyUseCase, Depends(_get_apply_use_case_dep)],
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
async def upload_schemas(
    env: Annotated[Environment, Form(..., description="업로드 대상 환경")],
    change_id: Annotated[ChangeId, Form(..., description="변경 ID")],
    files: Annotated[list[UploadFile], File(..., description="업로드할 스키마 파일 목록")],
    upload_use_case: Annotated[SchemaUploadUseCase, Depends(_get_upload_use_case_dep)],
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


@router.post(
    "/delete/analyze",
    response_model=SchemaDeleteImpactResponse,
    status_code=status.HTTP_200_OK,
    summary="스키마 삭제 영향도 분석",
    description="스키마 삭제 전 영향도를 분석합니다. 실제 삭제는 수행하지 않습니다.",
)
async def analyze_schema_delete_impact(
    subject: str,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    strategy: str = "TopicNameStrategy",
) -> SchemaDeleteImpactResponse:
    """스키마 삭제 영향도 분석"""
    try:
        # Use Case 생성
        audit_repo = cast(ISchemaAuditRepository, MySQLSchemaAuditRepository(session))
        use_case = SchemaDeleteAnalysisUseCase(
            registry_repository=container.schema_registry_repository(),
            audit_repository=audit_repo,
        )

        # 영향도 분석 수행
        strategy_enum = DomainSubjectStrategy(strategy)
        impact = await use_case.analyze(
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
async def delete_schema(
    subject: str,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    strategy: str = "TopicNameStrategy",
    force: bool = False,
) -> SchemaDeleteImpactResponse:
    """스키마 삭제 (영향도 분석 포함)"""
    try:
        # Use Case 생성
        audit_repo = cast(ISchemaAuditRepository, MySQLSchemaAuditRepository(session))
        use_case = SchemaDeleteAnalysisUseCase(
            registry_repository=container.schema_registry_repository(),
            audit_repository=audit_repo,
        )

        # 삭제 실행
        strategy_enum = DomainSubjectStrategy(strategy)
        impact = await use_case.delete(
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
    "/health",
    status_code=status.HTTP_200_OK,
    summary="스키마 모듈 헬스체크",
    description="스키마 모듈의 기본 헬스 상태를 확인합니다.",
)
async def health_check() -> ORJSONResponse:
    """헬스체크"""
    return ORJSONResponse(
        content={
            "status": "healthy",
            "module": "schema",
            "version": "1.0.0",
        }
    )
