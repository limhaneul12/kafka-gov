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
    TopicBatchApplyResponse,
    TopicBatchDryRunResponse,
    TopicBatchRequest,
    TopicBulkDeleteResponse,
    TopicListItem,
    TopicListResponse,
)

router = APIRouter(prefix="/v1/topics", tags=["topics"])

# =============================================================================
# Dependency Injection - @inject 데코레이터로 엔드포인트에 직접 주입
# =============================================================================
ListTopicDep = Depends(Provide[AppContainer.topic_container.list_use_case])
DryTopicDep = Depends(Provide[AppContainer.topic_container.dry_run_use_case])
ApplyTopicDep = Depends(Provide[AppContainer.topic_container.apply_use_case])


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
                tags=topic.get("tags", []),
                partition_count=topic.get("partition_count"),
                replication_factor=topic.get("replication_factor"),
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

        # 모든 토픽을 병렬로 삭제 (gather는 이미 리스트 반환)
        results_tuple = await asyncio.gather(*[delete_single_topic(name) for name in topic_names])
        results: list[tuple[str, bool]] = list(results_tuple)

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
