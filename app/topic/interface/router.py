"""Topic 모듈 라우터 - YAML 기반 토픽 배치 관리"""

from __future__ import annotations

import logging

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.container import AppContainer
from app.shared.roles import DEFAULT_USER
from app.topic.application.use_cases import TopicBulkDeleteUseCase
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

# Dependency Injection Shortcuts
DryTopicDep = Depends(Provide[AppContainer.topic_container.dry_run_use_case])
ApplyTopicDep = Depends(Provide[AppContainer.topic_container.apply_use_case])
ListTopicDep = Depends(Provide[AppContainer.topic_container.list_use_case])
BulkDeleteDep = Depends(Provide[AppContainer.topic_container.bulk_delete_use_case])


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
                doc=topic.get("doc"),
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
    "/batch/upload",
    response_model=TopicBatchDryRunResponse,
    status_code=status.HTTP_200_OK,
    summary="YAML 파일 업로드 및 Dry-Run",
    description="YAML 파일을 업로드하여 토픽 배치 변경 계획을 생성합니다.",
    response_description="파싱된 YAML의 Dry-Run 결과",
)
@inject
async def upload_yaml_and_dry_run(
    file: UploadFile = File(...), dry_run_use_case=DryTopicDep
) -> TopicBatchDryRunResponse:
    """안전한 YAML 파일 업로드 및 Dry-Run"""
    try:
        # 1. 파일 타입 검증
        if not file.filename or not file.filename.endswith((".yaml", ".yml")):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only YAML files (.yaml, .yml) are allowed",
            )

        # 2. YAML 컨텐츠 읽기
        content = await file.read()
        if not content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Empty file",
            )

        # 3. YAML 파싱
        import yaml

        try:
            yaml_data = yaml.safe_load(content)
        except yaml.YAMLError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid YAML format: {e!s}",
            ) from e

        # 4. TopicBatchRequest로 변환
        if not isinstance(yaml_data, dict):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="YAML must be a dictionary with 'kind', 'env', 'change_id', 'items'",
            )

        # 필수 필드 검증
        if yaml_data.get("kind") != "TopicBatch":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="kind must be 'TopicBatch'",
            )

        request = TopicBatchRequest(**yaml_data)

        # 5. Dry-Run 실행
        batch = safe_convert_request_to_batch(request)
        plan = await dry_run_use_case.execute(batch, DEFAULT_USER)
        return safe_convert_plan_to_response(plan, request)

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Validation error: {e!s}",
        ) from e
    except Exception as e:
        logging.getLogger(__name__).error(f"YAML upload failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process YAML: {e!s}",
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
    topic_names: list[str],
    bulk_delete_use_case: TopicBulkDeleteUseCase = BulkDeleteDep,
) -> TopicBulkDeleteResponse:
    """토픽 일괄 삭제 - Use Case 패턴"""
    try:
        result = await bulk_delete_use_case.execute(topic_names, DEFAULT_USER)

        return TopicBulkDeleteResponse(
            succeeded=result["succeeded"],
            failed=result["failed"],
            message=result["message"],
        )

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
async def delete_topic(
    name: str,
    bulk_delete_use_case: TopicBulkDeleteUseCase = BulkDeleteDep,
) -> dict[str, str]:
    """토픽 단일 삭제 - BulkDeleteUseCase 재사용"""
    try:
        result = await bulk_delete_use_case.execute([name], DEFAULT_USER)

        if result["failed"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete topic: {name}",
            )

        return {"message": f"Topic '{name}' deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete topic: {e!s}",
        ) from e
