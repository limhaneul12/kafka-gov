"""Topic 모듈 라우터 - YAML 기반 토픽 배치 관리"""

from typing import Annotated

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse

from app.container import AppContainer
from app.shared.error_handlers import handle_api_errors, handle_server_errors
from app.shared.roles import DEFAULT_USER
from app.topic.application.use_cases import (
    TopicBatchApplyFromYAMLUseCase,
    TopicBulkDeleteUseCase,
)
from app.topic.interface.adapters import (
    safe_convert_plan_to_response,
    safe_convert_request_to_batch,
)
from app.topic.interface.helpers import (
    parse_yaml_content,
    validate_yaml_file,
)
from app.topic.interface.schemas import (
    TopicBatchApplyResponse,
    TopicBatchDryRunResponse,
    TopicBatchRequest,
    TopicBatchYAMLRequest,
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
MetadataRepoDep = Depends(Provide[AppContainer.topic_container.metadata_repository])


@router.get(
    "",
    response_model=TopicListResponse,
    status_code=status.HTTP_200_OK,
    summary="토픽 목록 조회 (멀티 클러스터)",
    description="특정 Kafka 클러스터에 등록된 모든 토픽 목록을 조회합니다.",
    response_description="토픽 목록 조회 결과",
)
@inject
@handle_server_errors(error_message="토픽 목록 조회 실패")
async def list_topics(
    cluster_id: str = Query(..., description="Kafka Cluster ID"),
    use_case=ListTopicDep,
) -> TopicListResponse:
    """토픽 목록 조회"""
    topics_data = await use_case.execute(cluster_id)

    # dict를 TopicListItem으로 변환
    def _convert_owner_to_owners(topic_dict: dict) -> list[str]:
        """owner 또는 owners 필드를 owners 리스트로 변환"""
        if "owners" in topic_dict:
            return (
                topic_dict["owners"]
                if isinstance(topic_dict["owners"], list)
                else [topic_dict["owners"]]
            )
        if topic_dict.get("owner"):
            return (
                [topic_dict["owner"]]
                if isinstance(topic_dict["owner"], str)
                else topic_dict["owner"]
            )
        return []

    topics: list[TopicListItem] = [
        TopicListItem(
            name=topic["name"],
            owners=_convert_owner_to_owners(topic),
            doc=topic.get("doc"),
            tags=topic.get("tags", []),
            partition_count=topic.get("partition_count"),
            replication_factor=topic.get("replication_factor"),
            retention_ms=topic.get("retention_ms"),
            environment=topic["environment"],
            slo=topic.get("slo"),
            sla=topic.get("sla"),
        )
        for topic in topics_data
    ]

    return TopicListResponse(topics=topics)


@router.post(
    "/batch/upload",
    response_model=TopicBatchDryRunResponse,
    status_code=status.HTTP_200_OK,
    summary="토픽 배치 YAML 업로드 (Dry-Run)",
    description="YAML 파일 업로드 후 즉시 Dry-Run 수행합니다.",
    response_description="토픽 배치 계획",
)
@inject
@handle_api_errors(validation_error_message="YAML validation error")
async def upload_yaml_and_dry_run(
    file: Annotated[UploadFile, File(...)],
    cluster_id: str = Query(..., description="Kafka Cluster ID"),
    dry_run_use_case=DryTopicDep,
) -> TopicBatchDryRunResponse:
    """안전한 YAML 파일 업로드 및 Dry-Run"""
    # 1. 파일 타입 검증 (HTTPException 발생 가능 - pass-through)
    await validate_yaml_file(file)

    # 2. YAML 파싱 및 검증 (HTTPException 발생 가능 - pass-through)
    content = await file.read()
    yaml_data = await parse_yaml_content(content.decode("utf-8"))

    # 3. TopicBatchRequest로 변환
    request = TopicBatchRequest(**yaml_data)

    # 4. Dry-Run 실행
    batch = safe_convert_request_to_batch(request)
    plan = await dry_run_use_case.execute(cluster_id, batch, DEFAULT_USER)
    return safe_convert_plan_to_response(plan, request)


@router.post(
    "/batch/dry-run",
    response_model=TopicBatchDryRunResponse,
    status_code=status.HTTP_200_OK,
    summary="토픽 배치 Dry-Run (YAML 문자열)",
    description="YAML 문자열을 받아 토픽 배치 변경사항을 미리 확인합니다.",
    response_description="토픽 배치 계획",
)
@inject
@handle_api_errors(validation_error_message="Validation error")
async def topic_batch_dry_run_yaml(
    yaml_request: TopicBatchYAMLRequest,
    cluster_id: str = Query(..., description="Kafka Cluster ID"),
    dry_run_use_case=DryTopicDep,
) -> TopicBatchDryRunResponse:
    """YAML 기반 토픽 배치 Dry-Run"""
    # 1. YAML 파싱 및 검증 (Interface 레이어 책임)
    yaml_data = await parse_yaml_content(yaml_request.yaml_content)
    batch_request = TopicBatchRequest(**yaml_data)

    # 2. DTO → Domain 변환 (Adapter 책임)
    batch = safe_convert_request_to_batch(batch_request)

    # 3. 비즈니스 로직 실행 (UseCase 호출)
    plan = await dry_run_use_case.execute(cluster_id, batch, DEFAULT_USER)

    # 4. Domain → DTO 변환 (Adapter 책임)
    return safe_convert_plan_to_response(plan, batch_request)


@router.post(
    "/batch/dry-run/report",
    response_class=StreamingResponse,
    status_code=status.HTTP_200_OK,
    summary="Dry-Run Report 다운로드",
    description="Dry-Run 결과를 CSV 또는 JSON 형식으로 다운로드합니다.",
)
@inject
@handle_api_errors(validation_error_message="Validation error")
async def download_dry_run_report(
    batch_request: TopicBatchRequest,
    cluster_id: str = Query(..., description="Kafka Cluster ID"),
    format: str = Query("csv", regex="^(csv|json)$", description="Report format (csv/json)"),
    dry_run_use_case=DryTopicDep,
) -> StreamingResponse:
    """Dry-Run Report 다운로드

    Returns:
        StreamingResponse: CSV 또는 JSON 파일
    """
    # Dry-Run 실행
    batch = safe_convert_request_to_batch(batch_request)
    plan = await dry_run_use_case.execute(cluster_id, batch, DEFAULT_USER)

    # Plan -> Response 변환
    response = safe_convert_plan_to_response(plan, batch_request)

    # Report 생성 (Helper에 위임)
    from app.topic.interface.helpers import prepare_report_response

    content, media_type, filename = prepare_report_response(response, format, str(batch.change_id))

    return StreamingResponse(
        iter([content]),
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.post(
    "/batch/apply-yaml",
    response_model=TopicBatchApplyResponse,
    status_code=status.HTTP_200_OK,
    summary="YAML 기반 토픽 배치 Apply",
    description="YAML 문자열을 파싱하여 토픽 배치를 적용합니다. Backend에서 YAML 파싱 및 검증을 수행합니다.",
)
@inject
@handle_api_errors(validation_error_message="YAML parsing or policy violation")
async def topic_batch_apply_yaml(
    yaml_request: TopicBatchYAMLRequest,
    cluster_id: str = Query(..., description="Kafka Cluster ID"),
    apply_use_case=ApplyTopicDep,
) -> TopicBatchApplyResponse:
    """YAML 기반 토픽 배치 Apply - UseCase에 위임"""
    # UseCase 생성 및 실행
    yaml_use_case = TopicBatchApplyFromYAMLUseCase(apply_use_case)
    return await yaml_use_case.execute(cluster_id, yaml_request.yaml_content, DEFAULT_USER)


@router.post(
    "/batch/apply",
    response_model=TopicBatchApplyResponse,
    status_code=status.HTTP_200_OK,
    summary="토픽 배치 Apply (멀티 클러스터)",
    description="토픽 배치 변경을 실제로 적용합니다. 정책 위반이 있으면 실패합니다.",
    response_description="토픽 배치 변경 결과",
)
@inject
@handle_api_errors(validation_error_message="Policy violation")
async def topic_batch_apply(
    batch_request: TopicBatchRequest,
    cluster_id: str = Query(..., description="Kafka Cluster ID"),
    apply_use_case=ApplyTopicDep,
) -> TopicBatchApplyResponse:
    """토픽 배치 Apply"""
    batch = safe_convert_request_to_batch(batch_request)
    result = await apply_use_case.execute(cluster_id, batch, DEFAULT_USER)
    return TopicBatchApplyResponse(
        env=batch_request.env,
        change_id=batch_request.change_id,
        applied=list(result.applied),
        skipped=list(result.skipped),
        failed=list(result.failed),
        audit_id=result.audit_id,
        summary=result.summary(),
    )


@router.post(
    "/bulk-delete",
    status_code=status.HTTP_200_OK,
    summary="토픽 일괄 삭제 (멀티 클러스터)",
    description="여러 토픽을 한 번에 삭제합니다.",
    response_model=TopicBulkDeleteResponse,
)
@inject
@handle_server_errors(error_message="Failed to delete topics")
async def bulk_delete_topics(
    topic_names: list[str],
    cluster_id: str = Query(..., description="Kafka Cluster ID"),
    bulk_delete_use_case: TopicBulkDeleteUseCase = BulkDeleteDep,
) -> TopicBulkDeleteResponse:
    """토픽 일괄 삭제 - Use Case 패턴"""
    result = await bulk_delete_use_case.execute(cluster_id, topic_names, DEFAULT_USER)

    return TopicBulkDeleteResponse(
        succeeded=result["succeeded"],
        failed=result["failed"],
        message=result["message"],
    )


@router.patch(
    "/{name}/metadata",
    status_code=status.HTTP_200_OK,
    summary="토픽 메타데이터 업데이트",
    description="토픽의 메타데이터(owner, doc, tags, environment)를 업데이트합니다.",
)
@inject
@handle_server_errors(error_message="Failed to update topic metadata")
async def update_topic_metadata(
    name: str,
    metadata: dict[str, str | list[str] | None],
    cluster_id: str = Query(..., description="Kafka Cluster ID"),
    metadata_repo=MetadataRepoDep,
) -> dict[str, str]:
    """토픽 메타데이터 업데이트"""
    # metadata_repo는 save_topic_metadata를 사용하여 저장
    await metadata_repo.save_topic_metadata(name, metadata)
    return {"message": f"Topic metadata for '{name}' updated successfully"}


@router.delete(
    "/{name}",
    status_code=status.HTTP_200_OK,
    summary="토픽 삭제 (멀티 클러스터)",
    description="지정한 토픽을 Kafka에서 삭제합니다.",
)
@inject
@handle_server_errors(error_message="Failed to delete topic")
async def delete_topic(
    name: str,
    cluster_id: str = Query(..., description="Kafka Cluster ID"),
    bulk_delete_use_case: TopicBulkDeleteUseCase = BulkDeleteDep,
) -> dict[str, str]:
    """토픽 단일 삭제 - BulkDeleteUseCase 재사용"""
    result = await bulk_delete_use_case.execute(cluster_id, [name], DEFAULT_USER)

    if result["failed"]:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete topic: {name}",
        )

    return {"message": f"Topic '{name}' deleted successfully"}
