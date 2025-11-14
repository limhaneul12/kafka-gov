"""메트릭 수집 Celery Tasks"""

from __future__ import annotations

import asyncio
import atexit
import logging
from collections.abc import Coroutine
from typing import Any, TypeVar

from app.celery_app import celery_app
from app.container import AppContainer
from app.topic.infrastructure.adapter.metrics.collector import TopicMetricsCollector

logger = logging.getLogger(__name__)


T = TypeVar("T")


_WORKER_LOOP: asyncio.AbstractEventLoop | None = None


def _get_worker_loop() -> asyncio.AbstractEventLoop:
    global _WORKER_LOOP
    if _WORKER_LOOP is None or _WORKER_LOOP.is_closed():
        _WORKER_LOOP = asyncio.new_event_loop()
    return _WORKER_LOOP


def _run_in_worker_loop[T](coro: Coroutine[Any, Any, T]) -> T:
    """Celery 워커에서 공용 이벤트 루프로 코루틴 실행"""
    loop = _get_worker_loop()

    if loop.is_running():
        future = asyncio.run_coroutine_threadsafe(coro, loop)
        return future.result()

    try:
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)
    finally:
        asyncio.set_event_loop(None)


@atexit.register
def _close_worker_loop() -> None:
    global _WORKER_LOOP
    if _WORKER_LOOP and not _WORKER_LOOP.is_closed():
        _WORKER_LOOP.close()


async def _collect_and_store_metrics_async(cluster_id: str) -> None:
    """메트릭 수집 및 저장 (비동기)

    Args:
        cluster_id: 클러스터 ID
    """
    logger.info("Starting metrics collection for cluster: %s", cluster_id)

    try:
        # 1. AdminClient 주입 기반 메트릭 수집
        connection_manager = AppContainer.cluster_container.connection_manager()
        admin_client = await connection_manager.get_kafka_py_admin_client(cluster_id)
        collector = TopicMetricsCollector(
            admin_client=admin_client,
            cluster_id=cluster_id,
            ttl_seconds=0,
        )
        await collector.refresh()

        metrics = await collector.get_all_topic_metrics()
        leader_distribution = await collector.get_leader_distribution()

        if not metrics:
            logger.warning("No metrics collected for cluster: %s", cluster_id)
            return

        # 2. DB 저장 (DI Container 사용)
        repository = AppContainer.topic_container.metrics_repository()
        snapshot_id = await repository.save_snapshot(
            cluster_id=cluster_id,
            metrics=metrics,
            leader_distribution=leader_distribution,
        )
        logger.info(
            "Metrics snapshot saved successfully. Cluster: %s, Snapshot ID: %s",
            cluster_id,
            snapshot_id,
        )

    except Exception as exc:  # pragma: no cover - defensive log
        logger.error(
            "Failed to collect/store metrics for cluster %s: %s", cluster_id, exc, exc_info=True
        )
        raise


@celery_app.task(name="app.tasks.metrics_tasks.collect_and_store_metrics", bind=True)
def collect_and_store_metrics(self) -> dict[str, str | list[str]]:
    """모든 클러스터의 메트릭 수집 및 저장 (Celery Task)

    Returns:
        실행 결과
    """
    # 활성 클러스터 목록 조회
    list_use_case = AppContainer.cluster_container.list_kafka_clusters_use_case()
    clusters = _run_in_worker_loop(list_use_case.execute(active_only=True))

    if not clusters:
        logger.info("No active Kafka clusters found. Skipping metrics collection.")
        return {"status": "completed", "results": ["No active clusters"]}

    results: list[str] = []
    for cluster in clusters:
        try:
            _run_in_worker_loop(_collect_and_store_metrics_async(cluster_id=cluster.cluster_id))
            results.append(f"✅ {cluster.cluster_id!s}: Success")
        except Exception as exc:  # pragma: no cover - logging only
            logger.error("Failed for cluster %s: %s", cluster.cluster_id, exc)
            results.append(f"❌ {cluster.cluster_id!s}: {exc!s}")

    return {"status": "completed", "results": results}


async def _cleanup_old_snapshots_async(cluster_id: str, days: int) -> int:
    """오래된 스냅샷 정리 (비동기)

    Args:
        cluster_id: 클러스터 ID
        days: 보관 기간 (일)

    Returns:
        삭제된 개수
    """
    logger.info("Cleaning up old snapshots for cluster: %s (older than %s days)", cluster_id, days)

    repository = AppContainer.topic_container.metrics_repository()
    deleted_count = await repository.delete_old_snapshots(cluster_id, days)
    logger.info("Deleted %s old snapshots for cluster: %s", deleted_count, cluster_id)
    return deleted_count


@celery_app.task(name="app.tasks.metrics_tasks.cleanup_old_snapshots", bind=True)
def cleanup_old_snapshots(self, days: int = 7) -> dict[str, int | str]:
    """오래된 스냅샷 정리 (Celery Task)

    Args:
        days: 보관 기간 (일)

    Returns:
        삭제 결과
    """
    # 활성 클러스터 목록 조회
    list_use_case = AppContainer.cluster_container.list_kafka_clusters_use_case()
    clusters = _run_in_worker_loop(list_use_case.execute(active_only=True))

    total_deleted = 0
    for cluster in clusters:
        try:
            deleted = _run_in_worker_loop(_cleanup_old_snapshots_async(cluster.cluster_id, days))
            total_deleted += deleted
        except Exception as exc:  # pragma: no cover - logging only
            logger.error("Failed to cleanup for cluster %s: %s", cluster.cluster_id, exc)

    return {"status": "completed", "total_deleted": total_deleted}


@celery_app.task(name="app.tasks.metrics_tasks.manual_sync_metrics", bind=True)
def manual_sync_metrics(self, cluster_id: str) -> dict[str, str]:
    """수동 메트릭 동기화 (동기화 버튼용)

    Args:
        cluster_id: 클러스터 ID

    Returns:
        실행 결과
    """
    try:
        _run_in_worker_loop(_collect_and_store_metrics_async(cluster_id=cluster_id))
        return {"status": "success", "message": f"Metrics synced for {cluster_id}"}
    except Exception as exc:  # pragma: no cover - logging only
        logger.error("Manual sync failed for %s: %s", cluster_id, exc, exc_info=True)
        return {"status": "error", "message": str(exc)}
