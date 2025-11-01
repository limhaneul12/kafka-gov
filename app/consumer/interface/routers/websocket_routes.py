"""Consumer WebSocket Routes

실시간 Consumer Group 모니터링 WebSocket 엔드포인트
"""

import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.consumer.application.services import ConsumerGroupLiveCollector
from app.consumer.infrastructure.kafka_consumer_adapter import KafkaConsumerAdapter
from app.consumer.interface.schema.live_schema import LiveStreamEvent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws/consumers", tags=["Consumer WebSocket"])


@router.websocket("/groups/{group_id}/live")
async def stream_consumer_group_live(
    websocket: WebSocket,
    group_id: str,
    cluster_id: str,
    interval: int = 10,
) -> None:
    """Consumer Group 실시간 모니터링 스트림

    10초마다 스냅샷을 수집하여 전송
    - 단일 타임스탬프로 데이터 일관성 보장
    - Lag, Partition, Member 실시간 변화 감지
    - Rebalance/Stuck 이벤트 알림

    Args:
        websocket: WebSocket 연결
        group_id: Consumer Group ID
        cluster_id: 클러스터 ID
        interval: 갱신 주기 (기본 10초)
    """
    await websocket.accept()

    # 파라미터 검증
    if not cluster_id or cluster_id.strip() == "":
        logger.error(f"WebSocket connection failed: cluster_id is empty for group={group_id}")
        await websocket.send_json(
            LiveStreamEvent(
                type="error",
                data=None,
                message="cluster_id parameter is required",
            ).model_dump()
        )
        await websocket.close(code=1008, reason="Invalid cluster_id")
        return

    logger.info(
        f"WebSocket connected: cluster={cluster_id}, group={group_id}, interval={interval}s"
    )

    try:
        # ConnectionManager 가져오기 (app.state 통해 DI 컨테이너 접근)
        connection_manager = websocket.app.state.cluster_container.connection_manager()
        admin_client = await connection_manager.get_kafka_admin_client(cluster_id)

        # Live Collector 생성
        collector = ConsumerGroupLiveCollector(admin_client, cluster_id)

        # 연결 확인 메시지
        await websocket.send_json(
            LiveStreamEvent(
                type="connected",
                data=None,
                message=f"Connected to {group_id} (interval: {interval}s)",
            ).model_dump()
        )

        # 이전 상태 추적 (이벤트 감지용)
        prev_state: str | None = None
        prev_lag_spike: bool = False

        # 실시간 스트리밍 루프
        while True:
            try:
                # 스냅샷 수집
                snapshot = await collector.collect_live_snapshot(group_id)
            except KeyError:
                # 그룹이 삭제됨
                await websocket.send_json(
                    LiveStreamEvent(
                        type="error",
                        data=None,
                        message=f"Consumer group '{group_id}' not found",
                    ).model_dump()
                )
                break
            except Exception as e:
                # 일시적 오류는 계속 진행
                logger.warning(f"Snapshot collection failed: {e!r}")
                await asyncio.sleep(interval)
                continue

            # 이벤트 감지
            events: list[str] = []

            # State 변화 감지
            if prev_state and prev_state != snapshot.state:
                if snapshot.state == "Rebalancing":
                    events.append("⚠️ Rebalancing started")
                elif prev_state == "Rebalancing" and snapshot.state == "Stable":
                    events.append("✅ Rebalancing completed")

            # Lag Spike 감지
            if snapshot.has_lag_spike and not prev_lag_spike:
                events.append(f"🚨 Lag spike detected (max: {snapshot.lag_stats.max_lag:,})")

            # Stuck 파티션 감지
            if snapshot.stuck_count > 0:
                events.append(f"⚠️ {snapshot.stuck_count} stuck partition(s) detected")

            # 스냅샷 전송
            event = LiveStreamEvent(
                type="snapshot",
                data=snapshot,
                message="; ".join(events) if events else None,
            )
            await websocket.send_json(event.model_dump(mode="json"))

            # 상태 업데이트
            prev_state = snapshot.state
            prev_lag_spike = snapshot.has_lag_spike

            logger.debug(f"Snapshot sent: group={group_id}, lag={snapshot.lag_stats.total_lag}")

            # 다음 갱신까지 대기
            await asyncio.sleep(interval)

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: group={group_id}")

    except Exception as e:
        logger.error(f"WebSocket error: group={group_id}, error={e}", exc_info=True)


@router.websocket("/groups/stream")
async def stream_all_consumer_groups(
    websocket: WebSocket, cluster_id: str, interval: int = 30
) -> None:
    """전체 Consumer Group 목록 실시간 스트림

    대시보드용: 모든 그룹의 요약 정보를 주기적으로 전송

    Args:
        websocket: WebSocket 연결
        cluster_id: 클러스터 ID
        interval: 갱신 주기 (기본 30초)
    """
    await websocket.accept()

    # cluster_id 검증
    if not cluster_id or cluster_id.strip() == "":
        logger.error("WebSocket connection failed: cluster_id is empty")
        await websocket.send_json(
            LiveStreamEvent(
                type="error",
                data=None,
                message="cluster_id parameter is required",
            ).model_dump()
        )
        await websocket.close(code=1008, reason="Invalid cluster_id")
        return

    logger.info(f"WebSocket connected: cluster={cluster_id} (all groups stream)")

    try:
        # ConnectionManager 가져오기 (app.state 통해 DI 컨테이너 접근)
        connection_manager = websocket.app.state.cluster_container.connection_manager()
        admin_client = await connection_manager.get_kafka_admin_client(cluster_id)

        # Adapter 생성
        adapter = KafkaConsumerAdapter(admin_client)

        await websocket.send_json(
            LiveStreamEvent(
                type="connected",
                data=None,
                message=f"Connected to cluster {cluster_id} (interval: {interval}s)",
            ).model_dump()
        )

        while True:
            # 모든 그룹 목록 조회
            consumer_groups = await adapter.list_consumer_groups()

            # 각 그룹의 경량 스냅샷 수집
            collector = ConsumerGroupLiveCollector(admin_client, cluster_id)
            snapshots = []

            for group in consumer_groups[:20]:  # 최대 20개만 (성능 고려)
                try:
                    snapshot = await collector.collect_live_snapshot(group.group_id)
                    snapshots.append(snapshot)
                except KeyError:
                    # 그룹이 사라진 경우 무시
                    continue

            # 전송
            await websocket.send_json(
                LiveStreamEvent(
                    type="snapshot",
                    data={"groups": [s.model_dump(mode="json") for s in snapshots]},
                    message=None,
                ).model_dump()
            )

            logger.debug(f"All groups snapshot sent: count={len(snapshots)}")

            await asyncio.sleep(interval)

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: cluster={cluster_id} (all groups)")

    except Exception as e:
        logger.error(f"WebSocket error: cluster={cluster_id}, error={e}", exc_info=True)
