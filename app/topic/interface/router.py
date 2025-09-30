from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from app.shared.roles import DEFAULT_USER
from app.topic.application.use_cases import (
    TopicBatchApplyUseCase,
    TopicBatchDryRunUseCase,
    TopicDetailUseCase,
    TopicPlanUseCase,
)
from app.topic.container import (
    DbSession,
    get_apply_use_case,
    get_detail_use_case,
    get_dry_run_use_case,
    get_plan_use_case,
)
from app.topic.interface.adapters import (
    kafka_metadata_to_core_metadata,
    kafka_metadata_to_interface_config,
    safe_convert_plan_to_response,
    safe_convert_request_to_batch,
)
from app.topic.interface.schema import (
    ChangeId,
    TopicBatchApplyResponse,
    TopicBatchDryRunResponse,
    TopicBatchRequest,
    TopicDetailResponse,
    TopicPlanItem as ResponsePlanItem,
    TopicPlanResponse,
)

router = APIRouter(prefix="/v1/topics", tags=["topics"])


async def _get_dry_run_use_case_dep(
    session: DbSession,
) -> TopicBatchDryRunUseCase:
    """DI 경계의 레이트 바인딩을 보장해 테스트·운영 모두에서 교체 용이성 확보"""
    return await get_dry_run_use_case(session)


async def _get_apply_use_case_dep(
    session: DbSession,
) -> TopicBatchApplyUseCase:
    """DI 경계의 레이트 바인딩을 보장해 테스트·운영 모두에서 교체 용이성 확보"""
    return await get_apply_use_case(session)


def _get_detail_use_case_dep(session: DbSession) -> TopicDetailUseCase:
    """DI 경계의 레이트 바인딩을 보장해 테스트·운영 모두에서 교체 용이성 확보"""
    return get_detail_use_case(session)


def _get_plan_use_case_dep(session: DbSession) -> TopicPlanUseCase:
    """DI 경계의 레이트 바인딩을 보장해 테스트·운영 모두에서 교체 용이성 확보"""
    return get_plan_use_case(session)


@router.post(
    "/batch/dry-run",
    response_model=TopicBatchDryRunResponse,
    status_code=status.HTTP_200_OK,
    summary="토픽 배치 Dry-Run",
    description="토픽 배치 변경 계획을 생성하고 정책 위반을 검증합니다.",
)
async def topic_batch_dry_run(
    request: TopicBatchRequest,
    dry_run_use_case: Annotated[TopicBatchDryRunUseCase, Depends(_get_dry_run_use_case_dep)],
) -> TopicBatchDryRunResponse:
    """토픽 배치 Dry-Run"""
    try:
        batch = safe_convert_request_to_batch(request)
        plan = await dry_run_use_case.execute(batch, DEFAULT_USER)
        return safe_convert_plan_to_response(plan, request)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Validation error: {e!s}",
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {e!s}",
        ) from e


@router.post(
    "/batch/apply",
    response_model=TopicBatchApplyResponse,
    status_code=status.HTTP_200_OK,
    summary="토픽 배치 Apply",
    description="토픽 배치 변경을 실제로 적용합니다. 정책 위반이 있으면 실패합니다.",
)
async def topic_batch_apply(
    request: TopicBatchRequest,
    apply_use_case: Annotated[TopicBatchApplyUseCase, Depends(_get_apply_use_case_dep)],
) -> TopicBatchApplyResponse:
    """토픽 배치 Apply"""
    try:
        batch = safe_convert_request_to_batch(request)
        result = await apply_use_case.execute(batch, DEFAULT_USER)
        return TopicBatchApplyResponse(
            env=request.env,
            change_id=request.change_id,
            applied=list(result.applied),
            skipped=list(result.skipped),
            failed=list(result.failed),
            audit_id=result.audit_id,
            summary=result.summary(),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Policy violation: {e!s}",
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {e!s}",
        ) from e


@router.get(
    "/{name}",
    response_model=TopicDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="토픽 상세 조회",
    description="토픽의 상세 정보를 조회합니다 (Kafka 메타데이터 + 사용자 메타데이터).",
)
async def get_topic_detail(
    name: str,
    detail_use_case: Annotated[TopicDetailUseCase, Depends(_get_detail_use_case_dep)],
) -> TopicDetailResponse:
    """토픽 상세 조회"""
    try:
        result = await detail_use_case.execute(name)

        if result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Topic '{name}' not found",
            )

        # Kafka 메타데이터에서 config 및 핵심 메타데이터 변환
        raw_kafka_metadata = result.get("kafka_metadata", {})
        interface_config = kafka_metadata_to_interface_config(raw_kafka_metadata)
        if interface_config is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to derive topic config from Kafka metadata",
            )
        core_metadata = kafka_metadata_to_core_metadata(raw_kafka_metadata)

        # 응답 변환
        return TopicDetailResponse(
            name=name,
            config=interface_config,
            metadata=result.get("metadata"),
            kafka_metadata=core_metadata,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {e!s}",
        ) from e


@router.get(
    "/plans/{change_id}",
    response_model=TopicPlanResponse,
    status_code=status.HTTP_200_OK,
    summary="토픽 계획 조회",
    description="과거 실행된 토픽 배치 계획을 조회합니다.",
)
async def get_topic_plan(
    change_id: ChangeId,
    plan_use_case: Annotated[TopicPlanUseCase, Depends(_get_plan_use_case_dep)],
) -> TopicPlanResponse:
    """토픽 계획 조회"""
    try:
        plan = await plan_use_case.execute(change_id)

        if plan is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Plan '{change_id}' not found",
            )

        plan_items = [
            ResponsePlanItem(
                name=item.name,
                action=item.action.value,
                diff=item.diff,
                current_config=item.current_config,
                target_config=item.target_config,
            )
            for item in plan.items
        ]

        # 계약 보강: Repository에서 메타 정보 조회
        meta = await plan_use_case.get_meta(change_id)
        created_at = (
            meta.get("created_at", datetime.now(UTC).isoformat())
            if meta
            else datetime.now(UTC).isoformat()
        )
        status_value = (
            meta.get("status", ("applied" if plan.can_apply else "pending"))
            if meta
            else ("applied" if plan.can_apply else "pending")
        )
        applied_at = meta.get("applied_at") if meta else None

        return TopicPlanResponse(
            change_id=change_id,
            env=plan.env.value,
            status=status_value,
            created_at=created_at,
            applied_at=applied_at,
            plan=plan_items,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {e!s}",
        ) from e


@router.get(
    "/health",
    status_code=status.HTTP_200_OK,
    summary="토픽 모듈 헬스체크",
    description="토픽 모듈의 상태를 확인합니다.",
)
async def health_check() -> JSONResponse:
    """헬스체크"""
    return JSONResponse(
        content={
            "status": "healthy",
            "module": "topic",
            "version": "1.0.0",
        }
    )
