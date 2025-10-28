"""Consumer WebSocket 테스트"""

from datetime import datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.consumer.interface.routes.consumer_websocket import manager, publish_event
from app.main import app


@pytest.fixture(autouse=True)
def reset_manager():
    """각 테스트 전후 ConnectionManager 초기화"""
    # 테스트 전: 모든 연결 제거
    manager.active_connections.clear()
    yield
    # 테스트 후: 모든 연결 제거
    manager.active_connections.clear()


@pytest.fixture
def client():
    """FastAPI 테스트 클라이언트"""
    return TestClient(app)


@pytest.fixture
def sample_event():
    """샘플 WebSocket 이벤트"""
    return {
        "type": "lag_spike",
        "version": "v1",
        "ts": datetime.utcnow().isoformat(),
        "trace_id": str(uuid4()),
        "group_id": "test-group",
        "delta_total_lag": 4200,
        "current": {"total_lag": 8200, "p95_lag": 950, "max_lag": 2400},
        "window_s": 60,
        "thresholds": {"delta_total_lag": 2000},
    }


class TestWebSocketEndpoints:
    """WebSocket 엔드포인트 테스트"""

    def test_consumer_groups_stream_connection(self, client):
        """전체 그룹 스트림 연결 테스트"""
        # When
        with client.websocket_connect(
            "/ws/consumers/groups/stream?cluster_id=test-cluster"
        ) as websocket:
            # Then - 연결 성공
            assert websocket is not None

    def test_consumer_group_detail_stream_connection(self, client):
        """특정 그룹 스트림 연결 테스트"""
        # When
        with client.websocket_connect(
            "/ws/consumers/groups/test-group?cluster_id=test-cluster"
        ) as websocket:
            # Then - 연결 성공
            assert websocket is not None


class TestConnectionManager:
    """ConnectionManager 테스트"""

    @pytest.mark.asyncio
    async def test_connect_and_disconnect(self):
        """연결 및 연결 해제 테스트"""
        # Given
        from unittest.mock import AsyncMock

        websocket = AsyncMock()
        channel = "test_channel"

        # When - 연결
        await manager.connect(websocket, channel)

        # Then
        assert channel in manager.active_connections
        assert websocket in manager.active_connections[channel]

        # When - 연결 해제
        manager.disconnect(websocket, channel)

        # Then
        assert websocket not in manager.active_connections.get(channel, [])

    @pytest.mark.asyncio
    async def test_broadcast(self):
        """브로드캐스트 테스트"""
        # Given
        from unittest.mock import AsyncMock

        websocket1 = AsyncMock()
        websocket2 = AsyncMock()
        channel = "test_channel"
        message = {"type": "test", "data": "hello"}

        # When
        await manager.connect(websocket1, channel)
        await manager.connect(websocket2, channel)
        await manager.broadcast(channel, message)

        # Then
        websocket1.send_json.assert_called_once_with(message)
        websocket2.send_json.assert_called_once_with(message)


class TestPublishEvent:
    """publish_event 함수 테스트"""

    @pytest.mark.asyncio
    async def test_publish_event_to_all_stream(self, sample_event):
        """전체 스트림에 이벤트 발행"""
        # Given
        from unittest.mock import AsyncMock, patch

        cluster_id = "test-cluster"

        # When
        with patch.object(manager, "broadcast", new_callable=AsyncMock) as mock_broadcast:
            await publish_event(cluster_id, sample_event)

            # Then
            mock_broadcast.assert_called_once()
            call_args = mock_broadcast.call_args
            assert call_args[0][0] == f"consumer_stream_{cluster_id}"
            assert call_args[0][1] == sample_event

    @pytest.mark.asyncio
    async def test_publish_event_to_group_stream(self, sample_event):
        """그룹별 스트림에 이벤트 발행"""
        # Given
        from unittest.mock import AsyncMock, patch

        cluster_id = "test-cluster"
        group_id = "test-group"

        # When
        with patch.object(manager, "broadcast", new_callable=AsyncMock) as mock_broadcast:
            await publish_event(cluster_id, sample_event, group_id=group_id)

            # Then
            assert mock_broadcast.call_count == 2  # 전체 + 그룹별
            calls = [call[0][0] for call in mock_broadcast.call_args_list]
            assert f"consumer_stream_{cluster_id}" in calls
            assert f"consumer_group_{cluster_id}_{group_id}" in calls


class TestWebSocketEventSchema:
    """WebSocket 이벤트 스키마 테스트"""

    def test_event_common_header(self, sample_event):
        """공통 헤더 필드 검증"""
        # Then
        assert "type" in sample_event
        assert "version" in sample_event
        assert sample_event["version"] == "v1"
        assert "ts" in sample_event
        assert "trace_id" in sample_event

    def test_lag_spike_event_schema(self, sample_event):
        """Lag Spike 이벤트 스키마 검증"""
        # Then
        assert sample_event["type"] == "lag_spike"
        assert "group_id" in sample_event
        assert "delta_total_lag" in sample_event
        assert "current" in sample_event
        assert "window_s" in sample_event
        assert "thresholds" in sample_event

    def test_event_trace_id_uniqueness(self):
        """trace_id 고유성 검증"""
        # Given
        events = [
            {
                "type": "lag_spike",
                "version": "v1",
                "ts": datetime.utcnow().isoformat(),
                "trace_id": str(uuid4()),
                "group_id": "test-group",
            }
            for _ in range(100)
        ]

        # When
        trace_ids = [e["trace_id"] for e in events]

        # Then
        assert len(trace_ids) == len(set(trace_ids))  # 모두 고유


class TestWebSocketReconnection:
    """WebSocket 재연결 시나리오 테스트"""

    @pytest.mark.asyncio
    async def test_client_reconnection(self):
        """클라이언트 재연결 시나리오"""
        # Given
        from unittest.mock import AsyncMock

        websocket = AsyncMock()
        channel = "test_channel"

        # When - 첫 번째 연결
        await manager.connect(websocket, channel)
        assert websocket in manager.active_connections[channel]

        # When - 연결 해제
        manager.disconnect(websocket, channel)
        assert websocket not in manager.active_connections.get(channel, [])

        # When - 재연결
        await manager.connect(websocket, channel)

        # Then - 재연결 성공
        assert websocket in manager.active_connections[channel]
