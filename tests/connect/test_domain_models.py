"""Connect Domain Models 테스트"""

from datetime import datetime, timezone

import pytest

from app.connect.domain.models import (
    ConnectorConfig,
    ConnectorInfo,
    ConnectorPlugin,
    ConnectorState,
    ConnectorStatus,
    ConnectorType,
    TaskInfo,
    TaskState,
)
from app.connect.domain.models_metadata import ConnectorMetadata


class TestConnectorType:
    """ConnectorType Enum 테스트"""

    def test_connector_type_values(self):
        """커넥터 타입 값 확인"""
        assert ConnectorType.SOURCE.value == "source"
        assert ConnectorType.SINK.value == "sink"

    def test_connector_type_from_string(self):
        """문자열에서 타입 변환"""
        assert ConnectorType("source") == ConnectorType.SOURCE
        assert ConnectorType("sink") == ConnectorType.SINK


class TestConnectorState:
    """ConnectorState Enum 테스트"""

    def test_connector_state_values(self):
        """커넥터 상태 값 확인"""
        assert ConnectorState.RUNNING.value == "RUNNING"
        assert ConnectorState.PAUSED.value == "PAUSED"
        assert ConnectorState.FAILED.value == "FAILED"
        assert ConnectorState.UNASSIGNED.value == "UNASSIGNED"

    def test_state_comparison(self):
        """상태 비교"""
        assert ConnectorState.RUNNING == ConnectorState.RUNNING
        assert ConnectorState.RUNNING != ConnectorState.FAILED


class TestTaskState:
    """TaskState Enum 테스트"""

    def test_task_state_values(self):
        """태스크 상태 값 확인"""
        assert TaskState.RUNNING.value == "RUNNING"
        assert TaskState.PAUSED.value == "PAUSED"
        assert TaskState.FAILED.value == "FAILED"
        assert TaskState.UNASSIGNED.value == "UNASSIGNED"

    def test_state_comparison(self):
        """상태 비교"""
        assert TaskState.RUNNING == TaskState.RUNNING
        assert TaskState.RUNNING != TaskState.FAILED


class TestConnectorInfo:
    """ConnectorInfo 모델 테스트"""

    def test_connector_info_creation(self):
        """커넥터 정보 생성"""
        info = ConnectorInfo(
            name="test-connector",
            type=ConnectorType.SINK,
            state=ConnectorState.RUNNING,
            worker_id="worker-1",
            config={"connector.class": "io.confluent.connect.s3.S3SinkConnector"},
            tasks=[],
        )

        assert info.name == "test-connector"
        assert info.type == ConnectorType.SINK
        assert info.state == ConnectorState.RUNNING
        assert info.config["connector.class"] == "io.confluent.connect.s3.S3SinkConnector"
        assert len(info.tasks) == 0

    def test_connector_info_immutable(self):
        """불변성 확인"""
        info = ConnectorInfo(
            name="test-connector",
            type=ConnectorType.SINK,
            state=ConnectorState.RUNNING,
            worker_id="worker-1",
            config={},
            tasks=[],
        )

        with pytest.raises((AttributeError, TypeError)):
            info.name = "new-name"  # frozen=True이므로 변경 불가


class TestConnectorStatus:
    """ConnectorStatus 모델 테스트"""

    def test_connector_status_creation(self):
        """커넥터 상태 생성"""
        status = ConnectorStatus(
            name="test-connector",
            connector={"state": "RUNNING", "worker_id": "worker-1"},
            tasks=[],
            type=ConnectorType.SINK,
        )

        assert status.name == "test-connector"
        assert status.connector["state"] == "RUNNING"
        assert status.type == ConnectorType.SINK

    def test_connector_status_with_tasks(self):
        """태스크가 있는 커넥터 상태"""
        status = ConnectorStatus(
            name="test-connector",
            connector={"state": "RUNNING", "worker_id": "worker-1"},
            tasks=[
                {"id": "0", "state": "RUNNING", "worker_id": "worker-1"},
                {"id": "1", "state": "FAILED", "worker_id": "worker-2"},
            ],
            type=ConnectorType.SINK,
        )

        assert len(status.tasks) == 2
        assert status.tasks[0]["state"] == "RUNNING"
        assert status.tasks[1]["state"] == "FAILED"


class TestTaskInfo:
    """TaskInfo 모델 테스트"""

    def test_task_info_creation(self):
        """태스크 정보 생성"""
        task = TaskInfo(
            id=0,
            state=TaskState.RUNNING,
            worker_id="worker-1",
            trace=None,
        )

        assert task.id == 0
        assert task.state == TaskState.RUNNING
        assert task.worker_id == "worker-1"

    def test_task_info_with_trace(self):
        """에러 trace가 있는 태스크"""
        task = TaskInfo(
            id=0,
            state=TaskState.FAILED,
            worker_id="worker-1",
            trace="java.lang.Exception: Connection failed",
        )

        assert task.state == TaskState.FAILED
        assert task.trace is not None
        assert "Connection failed" in task.trace


class TestConnectorMetadata:
    """ConnectorMetadata 모델 테스트"""

    def test_metadata_creation(self):
        """메타데이터 생성"""
        now = datetime.now(timezone.utc)
        metadata = ConnectorMetadata(
            id="meta-123",
            connect_id="test-connect",
            connector_name="test-connector",
            team="data-platform",
            tags=["production", "critical"],
            description="Test connector",
            owner="admin@example.com",
            created_at=now,
            updated_at=now,
        )

        assert metadata.id == "meta-123"
        assert metadata.connector_name == "test-connector"
        assert metadata.team == "data-platform"
        assert "production" in metadata.tags
        assert metadata.owner == "admin@example.com"

    def test_metadata_optional_fields(self):
        """선택적 필드가 없는 메타데이터"""
        metadata = ConnectorMetadata(
            id="meta-123",
            connect_id="test-connect",
            connector_name="test-connector",
            team=None,
            tags=[],
            description=None,
            owner=None,
            created_at=None,
            updated_at=None,
        )

        assert metadata.team is None
        assert len(metadata.tags) == 0
        assert metadata.description is None

    def test_metadata_immutable(self):
        """불변성 확인"""
        metadata = ConnectorMetadata(
            id="meta-123",
            connect_id="test-connect",
            connector_name="test-connector",
        )

        with pytest.raises((AttributeError, TypeError)):
            metadata.team = "new-team"  # frozen=True이므로 변경 불가
