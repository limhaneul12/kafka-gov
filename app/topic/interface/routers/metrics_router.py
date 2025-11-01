"""메트릭 API 라우터"""

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, status

from app.celery_app import celery_app
from app.container import AppContainer
from app.shared.error_handlers import handle_server_errors
from app.topic.infrastructure.adapter.metrics.collector import TopicMetricsCollector
from app.topic.interface.schemas.metrics_schemas import (
    ClusterMetricsResponse,
    TopicDistributionResponse,
    TopicMetricsResponse,
)

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get(
    "/topics/{topic_name}",
    response_model=TopicMetricsResponse,
    status_code=status.HTTP_200_OK,
    summary="특정 토픽 메트릭 조회",
    description="특정 토픽의 상세 메트릭 정보를 조회합니다.",
    response_description="토픽 메트릭 조회 결과",
)
@inject
@handle_server_errors(error_message="토픽 메트릭 조회 실패")
async def get_topic_metrics(
    topic_name: str,
    cluster_id: str,
    use_case=Depends(Provide[AppContainer.topic_container.get_topic_metrics_use_case]),
) -> TopicMetricsResponse:
    """특정 토픽의 메트릭 조회 (최신 스냅샷 기반)"""
    result = await use_case.execute(cluster_id=cluster_id, topic_name=topic_name)
    return TopicMetricsResponse(**result)


@router.get(
    "/topics/{topic_name}/live",
    response_model=TopicMetricsResponse,
    status_code=status.HTTP_200_OK,
    summary="특정 토픽 메트릭 실시간 조회",
    description="Kafka AdminClient를 통해 실시간 파티션 상세 정보를 조회합니다.",
    response_description="토픽 실시간 메트릭 조회 결과",
)
@inject
@handle_server_errors(error_message="토픽 실시간 메트릭 조회 실패")
async def get_topic_metrics_live(
    topic_name: str,
    cluster_id: str,
    connection_manager=Depends(Provide[AppContainer.cluster_container.connection_manager]),
) -> TopicMetricsResponse:
    """특정 토픽의 메트릭 실시간 조회"""
    admin_client = await connection_manager.get_kafka_py_admin_client(cluster_id)
    collector = TopicMetricsCollector(admin_client=admin_client, ttl_seconds=0)
    await collector.refresh()
    metrics = await collector.get_all_topic_metrics()

    if metrics is None or topic_name not in metrics.topic_meta:
        raise ValueError("No metrics found for topic")

    topic_meta = metrics.topic_meta[topic_name]
    partitions = topic_meta.partition_details

    total_size = sum(partition.partition_size for partition in partitions)
    max_size = max((partition.partition_size for partition in partitions), default=0)
    min_size = min((partition.partition_size for partition in partitions), default=0)
    avg_size = int(round(total_size / len(partitions), 0)) if partitions else 0

    return TopicMetricsResponse(
        topic_name=topic_name,
        partition_count=len(partitions),
        storage={
            "total_size": total_size,
            "max_partition_size": max_size,
            "min_partition_size": min_size,
            "avg_partition_size": avg_size,
        },
        partitions=[
            {
                "partition": partition.partition_index,
                "size": partition.partition_size,
                "leader": partition.leader,
                "replicas": partition.replicas,
                "isr": partition.isr,
                "offset_lag": partition.offset_lag,
            }
            for partition in partitions
        ],
    )


@router.get(
    "/topics",
    response_model=TopicDistributionResponse,
    status_code=status.HTTP_200_OK,
    summary="전체 토픽 분포 요약 조회",
    description="전체 토픽의 분포 및 요약 메트릭 정보를 조회합니다.",
    response_description="전체 토픽 분포 조회 결과",
)
@inject
@handle_server_errors(error_message="전체 토픽 분포 조회 실패")
async def get_all_topics_metrics(
    cluster_id: str,
    use_case=Depends(Provide[AppContainer.topic_container.get_topic_metrics_use_case]),
) -> TopicDistributionResponse:
    """전체 토픽 분포 요약 조회 (최신 스냅샷 기반)"""
    result = await use_case.execute(cluster_id=cluster_id, topic_name=None)
    return TopicDistributionResponse(**result)


@router.get(
    "/cluster",
    response_model=ClusterMetricsResponse,
    status_code=status.HTTP_200_OK,
    summary="클러스터 메트릭 조회",
    description="Kafka 클러스터의 전반적인 메트릭 정보를 조회합니다.",
    response_description="클러스터 메트릭 조회 결과",
)
@inject
@handle_server_errors(error_message="클러스터 메트릭 조회 실패")
async def get_cluster_metrics(
    cluster_id: str,
    use_case=Depends(Provide[AppContainer.topic_container.get_cluster_metrics_use_case]),
) -> ClusterMetricsResponse:
    """클러스터 메트릭 조회 (최신 스냅샷 기반)"""
    result = await use_case.execute(cluster_id=cluster_id)
    return ClusterMetricsResponse(**result)


@router.post(
    "/refresh",
    status_code=status.HTTP_200_OK,
    summary="메트릭 캐시 강제 갱신",
    description="메모리 캐시에 있는 메트릭 스냅샷을 강제로 갱신합니다. DB 저장은 /sync를 사용하세요.",
    response_description="갱신 완료 메시지",
)
@inject
@handle_server_errors(error_message="메트릭 캐시 갱신 실패")
async def refresh_metrics(cluster_id: str) -> dict[str, str]:
    """메트릭 동기화 태스크 트리거 (스냅샷 수집)"""
    task = celery_app.send_task("app.tasks.metrics_tasks.manual_sync_metrics", args=[cluster_id])
    return {"message": "Metrics sync started (refresh)", "task_id": task.id}


@router.post(
    "/sync",
    status_code=status.HTTP_202_ACCEPTED,
    summary="메트릭 동기화 (DB 저장)",
    description="Celery 태스크를 통해 비동기로 메트릭을 수집하고 DB에 저장합니다. 사용자가 동기화 버튼을 눌렀을 때 호출됩니다.",
    response_description="동기화 태스크 시작 메시지",
)
@inject
@handle_server_errors(error_message="메트릭 동기화 시작 실패")
async def sync_metrics_to_db(cluster_id: str) -> dict[str, str]:
    """메트릭 동기화 (DB 저장 포함)"""
    # Celery 태스크 비동기 실행
    task = celery_app.send_task("app.tasks.metrics_tasks.manual_sync_metrics", args=[cluster_id])

    return {
        "message": f"Metrics sync started for cluster: {cluster_id}",
        "task_id": task.id,
        "status": "processing",
    }
