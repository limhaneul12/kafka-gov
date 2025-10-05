import asyncio
import logging
from datetime import UTC, datetime

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, HTTPException, status

from app.container import AppContainer
from app.shared.roles import DEFAULT_USER
from app.topic.domain.models import (
    DomainEnvironment,
    DomainTopicAction,
    DomainTopicBatch,
    DomainTopicSpec,
)
from app.topic.interface.adapters import (
    safe_convert_plan_to_response,
    safe_convert_request_to_batch,
)
from app.topic.interface.schema import (
    ChangeId,
    TopicBatchApplyResponse,
    TopicBatchDryRunResponse,
    TopicBatchRequest,
    TopicBulkDeleteResponse,
    TopicDetailResponse,
    TopicListItem,
    TopicListResponse,
    TopicPlanItem as ResponsePlanItem,
    TopicPlanResponse,
)

router = APIRouter(prefix="/v1/topics", tags=["topics"])

# =============================================================================
# Dependency Injection - @inject 데코레이터로 엔드포인트에 직접 주입
# =============================================================================
ListTopicDep = Depends(Provide[AppContainer.topic_container.list_use_case])
DryTopicDep = Depends(Provide[AppContainer.topic_container.dry_run_use_case])
ApplyTopicDep = Depends(Provide[AppContainer.topic_container.apply_use_case])
DetailTopicDep = Depends(Provide[AppContainer.topic_container.detail_use_case])
PlanTopicDep = Depends(Provide[AppContainer.topic_container.plan_use_case])


@router.get(
    "",
    response_model=TopicListResponse,
    status_code=status.HTTP_200_OK,
    summary="토픽 목록 조회",
    description="Kafka에 등록된 모든 토픽 목록을 조회합니다.",
    response_description="토픽 목록 조회 결과",
)
@inject
async def list_topics(use_case=ListTopicDep) -> TopicListResponse:
    """토픽 목록 조회"""
    try:
        topics_data = await use_case.execute()

        # dict를 TopicListItem으로 변환
        topics: list[TopicListItem] = [
            TopicListItem(
                name=topic["name"],
                owner=topic.get("owner"),
                environment=topic["environment"],
            )
            for topic in topics_data
        ]

        return TopicListResponse(topics=topics)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"토픽 목록 조회 실패: {e!s}",
        ) from e


@router.post(
    "/batch/dry-run",
    response_model=TopicBatchDryRunResponse,
    status_code=status.HTTP_200_OK,
    summary="토픽 배치 Dry-Run",
    description="토픽 배치 변경 계획을 생성하고 정책 위반을 검증합니다.",
    response_description="토픽 배치 Dry-Run 결과",
)
@inject
async def topic_batch_dry_run(
    request: TopicBatchRequest, dry_run_use_case=DryTopicDep
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
    response_description="토픽 배치 변경 결과",
)
@inject
async def topic_batch_apply(
    request: TopicBatchRequest, apply_use_case=ApplyTopicDep
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
    "/plans/{change_id}",
    response_model=TopicPlanResponse,
    status_code=status.HTTP_200_OK,
    summary="토픽 계획 조회",
    description="과거 실행된 토픽 배치 계획을 조회합니다.",
    response_description="토픽 계획 조회 결과",
)
@inject
async def get_topic_plan(change_id: ChangeId, plan_use_case=PlanTopicDep) -> TopicPlanResponse:
    """토픽 계획 조회"""
    try:
        plan = await plan_use_case.execute(change_id)

        if plan is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Plan '{change_id}' not found",
            )

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

        # 계약 보강: Repository에서 메타 정보 조회
        meta = await plan_use_case.get_meta(change_id)
        created_at: str = (
            meta.get("created_at", datetime.now(UTC).isoformat())
            if meta
            else datetime.now(UTC).isoformat()
        )
        status_value: str = (
            meta.get("status", ("applied" if plan.can_apply else "pending"))
            if meta
            else ("applied" if plan.can_apply else "pending")
        )
        applied_at: str | None = meta.get("applied_at") if meta else None

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
    "/{name}",
    response_model=TopicDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="토픽 상세 조회",
    description="토픽의 상세 정보를 조회합니다 (Kafka 메타데이터 + 사용자 메타데이터).",
    response_description="토픽 상세 조회 결과",
)
@inject
async def get_topic_detail(name: str, detail_use_case=DetailTopicDep) -> TopicDetailResponse:
    """토픽 상세 조회"""
    try:
        result = await detail_use_case.execute(name)

        if result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Topic '{name}' not found",
            )

        # Kafka 메타데이터 변환 (dict 형식으로)
        raw_kafka_metadata = result.kafka_metadata

        # 디버깅: 메타데이터 구조 로깅
        logger = logging.getLogger(__name__)
        logger.info(f"Raw Kafka metadata for {name}: {raw_kafka_metadata}")

        # dict 형식으로 변환
        if raw_kafka_metadata is None:
            kafka_metadata_dict = {
                "partition_count": 0,
                "replication_factor": 0,
                "config": {},
            }
        else:
            kafka_metadata_dict = {
                "partition_count": raw_kafka_metadata.get("partition_count", 0),
                "replication_factor": raw_kafka_metadata.get("replication_factor", 0),
                "config": raw_kafka_metadata.get("config", {}),
            }

        # 응답 변환
        return TopicDetailResponse(
            name=name,
            kafka_metadata=kafka_metadata_dict,
            metadata=result.metadata,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {e!s}",
        ) from e


@router.post(
    "/bulk-delete",
    status_code=status.HTTP_200_OK,
    summary="토픽 일괄 삭제",
    description="여러 토픽을 한 번에 삭제합니다.",
    response_model=TopicBulkDeleteResponse,
)
@inject
async def bulk_delete_topics(
    topic_names: list[str], apply_use_case=ApplyTopicDep
) -> TopicBulkDeleteResponse:
    """토픽 일괄 삭제 - 병렬 처리"""
    try:
        if not topic_names:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No topics specified for deletion",
            )

        async def delete_single_topic(name: str) -> tuple[str, bool]:
            """단일 토픽 삭제 (성공 여부 반환)"""
            try:
                # 개별 배치 생성 (환경 무관)
                batch = DomainTopicBatch(
                    change_id=f"delete_{name}_{int(datetime.now(UTC).timestamp())}",
                    env=DomainEnvironment.UNKNOWN,
                    specs=(
                        DomainTopicSpec(
                            name=name,
                            action=DomainTopicAction.DELETE,
                            config=None,
                            metadata=None,
                        ),
                    ),
                )

                result = await apply_use_case.execute(batch, DEFAULT_USER)
                return (name, name in result.applied)

            except Exception as e:
                logging.getLogger(__name__).error(f"Failed to delete topic {name}: {e}")
                return (name, False)

        # 모든 토픽을 병렬로 삭제
        results: list[tuple[str, bool]] = list(
            await asyncio.gather(*[delete_single_topic(name) for name in topic_names])
        )

        # 결과 분류
        succeeded: list[str] = [name for name, success in results if success]
        failed: list[str] = [name for name, success in results if not success]

        return TopicBulkDeleteResponse(
            succeeded=succeeded,
            failed=failed,
            message=f"Deleted {len(succeeded)} topics, {len(failed)} failed",
        )

    except HTTPException:
        raise
    except Exception as e:
        logging.getLogger(__name__).error(f"Bulk delete failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete topics: {e!s}",
        ) from e


@router.delete(
    "/{name}",
    status_code=status.HTTP_200_OK,
    summary="토픽 삭제",
    description="지정한 토픽을 Kafka에서 삭제합니다.",
)
@inject
async def delete_topic(name: str, apply_use_case=ApplyTopicDep) -> dict[str, str]:
    """토픽 삭제"""
    try:
        # 배치 생성 (환경 무관)
        batch = DomainTopicBatch(
            change_id=f"delete_{name}_{int(datetime.now(UTC).timestamp())}",
            env=DomainEnvironment.UNKNOWN,
            specs=(
                DomainTopicSpec(
                    name=name,
                    action=DomainTopicAction.DELETE,
                    config=None,
                    metadata=None,
                ),
            ),
        )

        result = await apply_use_case.execute(batch, DEFAULT_USER)

        if name in result.failed:
            error = result.failed[name] if isinstance(result.failed, dict) else "Unknown error"
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete topic: {error}",
            )

        return {"message": f"Topic '{name}' deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete topic: {e!s}",
        ) from e
