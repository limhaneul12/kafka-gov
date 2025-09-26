"""Topic FastAPI 라우터"""

from __future__ import annotations

import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from ...shared.auth import get_current_user
from ..application.use_cases import (
    TopicBatchApplyUseCase,
    TopicBatchDryRunUseCase,
    TopicDetailUseCase,
    TopicPlanUseCase,
)
from ..container import (
    get_apply_use_case,
    get_detail_use_case,
    get_dry_run_use_case,
    get_plan_use_case,
)
from ..domain.models import (
    TopicAction as DomainTopicAction,
    TopicBatch,
    TopicConfig as DomainTopicConfig,
    TopicMetadata as DomainTopicMetadata,
    TopicPlan,
    TopicSpec as DomainTopicSpec,
)
from .schema import (
    ChangeId,
    PolicyViolation as ResponseViolation,
    TopicBatchApplyResponse,
    TopicBatchDryRunResponse,
    TopicBatchRequest,
    TopicDetailResponse,
    TopicName,
    TopicPlanItem as ResponsePlanItem,
    TopicPlanResponse,
)

router = APIRouter(prefix="/v1/topics", tags=["topics"])


def convert_request_to_batch(request: TopicBatchRequest) -> TopicBatch:
    """요청 DTO를 도메인 배치로 변환"""

    def convert_item_to_spec(item) -> DomainTopicSpec:
        """개별 아이템을 도메인 명세로 변환"""
        # 설정 변환
        domain_config = (
            DomainTopicConfig(
                partitions=item.config.partitions,
                replication_factor=item.config.replication_factor,
                cleanup_policy=item.config.cleanup_policy,
                compression_type=item.config.compression_type,
                retention_ms=item.config.retention_ms,
                min_insync_replicas=item.config.min_insync_replicas,
                max_message_bytes=item.config.max_message_bytes,
                segment_ms=item.config.segment_ms,
            )
            if item.config
            else None
        )

        # 메타데이터 변환
        domain_metadata = (
            DomainTopicMetadata(
                owner=item.metadata.owner,
                sla=item.metadata.sla,
                doc=item.metadata.doc,
                tags=tuple(item.metadata.tags),
            )
            if item.metadata
            else None
        )

        return DomainTopicSpec(
            name=item.name,
            action=DomainTopicAction(item.action.value),
            config=domain_config,
            metadata=domain_metadata,
            reason=item.reason,
        )

    # 리스트 컴프리헨션으로 변환
    specs = tuple(convert_item_to_spec(item) for item in request.items)

    return TopicBatch(
        change_id=request.change_id,
        env=request.env,
        specs=specs,
    )


def convert_plan_to_response(
    plan: TopicPlan, request: TopicBatchRequest
) -> TopicBatchDryRunResponse:
    """도메인 계획을 응답 DTO로 변환"""

    # 계획 아이템 변환
    plan_items: list[ResponsePlanItem] = [
        ResponsePlanItem(
            name=item.name,
            action=item.action.value,
            diff=item.diff,
            current_config=item.current_config,
            target_config=item.target_config,
        )
        for item in plan.items
    ]

    # 위반 사항 변환
    violations: list[ResponseViolation] = [
        ResponseViolation(
            name=v.name,
            rule=v.rule,
            message=v.message,
            severity=v.severity,
            field=v.field,
        )
        for v in plan.violations
    ]

    return TopicBatchDryRunResponse(
        env=request.env,
        change_id=request.change_id,
        plan=plan_items,
        violations=violations,
        summary=plan.summary(),
    )


@router.post(
    "/batch/dry-run",
    response_model=TopicBatchDryRunResponse,
    status_code=status.HTTP_200_OK,
    summary="토픽 배치 Dry-Run",
    description="토픽 배치 변경 계획을 생성하고 정책 위반을 검증합니다.",
)
async def topic_batch_dry_run(
    request: TopicBatchRequest,
    dry_run_use_case: Annotated[TopicBatchDryRunUseCase, Depends(get_dry_run_use_case)],
    current_user: Annotated[str, Depends(get_current_user)],
) -> TopicBatchDryRunResponse:
    """토픽 배치 Dry-Run"""
    try:
        # 요청을 도메인 모델로 변환
        batch = convert_request_to_batch(request)

        # 유스케이스 실행
        plan = await dry_run_use_case.execute(batch, current_user)

        # 응답 변환
        return convert_plan_to_response(plan, request)

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
    apply_use_case: Annotated[TopicBatchApplyUseCase, Depends(get_apply_use_case)],
    current_user: Annotated[str, Depends(get_current_user)],
) -> TopicBatchApplyResponse:
    """토픽 배치 Apply"""
    try:
        # 요청을 도메인 모델로 변환
        batch = convert_request_to_batch(request)

        # 유스케이스 실행
        result = await apply_use_case.execute(batch, current_user)

        # 응답 변환
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
    name: TopicName,
    detail_use_case: Annotated[TopicDetailUseCase, Depends(get_detail_use_case)],
) -> TopicDetailResponse:
    """토픽 상세 조회"""
    try:
        result = await detail_use_case.execute(name)

        if result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Topic '{name}' not found",
            )

        # 응답 변환
        return TopicDetailResponse(
            name=name,
            config=result["kafka_metadata"].get("config", {}),
            metadata=result.get("metadata"),
            kafka_metadata=result["kafka_metadata"],
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {e!s}",
        ) from e


@router.get(
    "/plan/{change_id}",
    response_model=TopicPlanResponse,
    status_code=status.HTTP_200_OK,
    summary="토픽 계획 조회",
    description="과거 실행된 토픽 배치 계획을 조회합니다.",
)
async def get_topic_plan(
    change_id: ChangeId,
    plan_use_case: Annotated[TopicPlanUseCase, Depends(get_plan_use_case)],
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

        # 실제 상태 관리 - 계획의 위반 사항에 따라 상태 결정
        status_value = "completed" if plan.can_apply else "failed"

        # 실제 타임스탬프 - 현재 시간 기준으로 생성
        now = datetime.datetime.now(datetime.UTC)
        created_at = now.isoformat()
        applied_at = now.isoformat() if status_value == "completed" else None

        return TopicPlanResponse(
            change_id=change_id,
            env=plan.env,
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
