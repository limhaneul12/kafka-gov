"""테스트용 Mock 객체들"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock


class MockKafkaAdminClient:
    """Mock Kafka AdminClient"""

    def __init__(self):
        self.list_topics = AsyncMock(return_value={"topics": []})
        self.create_topics = AsyncMock(return_value={})
        self.delete_topics = AsyncMock(return_value={})
        self.describe_configs = AsyncMock(return_value={})
        self.alter_configs = AsyncMock(return_value={})


class MockSchemaRegistryClient:
    """Mock Schema Registry Client"""

    def __init__(self):
        self.register_schema = AsyncMock(return_value=1)
        self.get_schema = AsyncMock(return_value=None)
        self.get_subjects = AsyncMock(return_value=[])
        self.get_versions = AsyncMock(return_value=[])
        self.delete_subject = AsyncMock(return_value=[])
        self.test_compatibility = AsyncMock(return_value=True)
        self.get_compatibility = AsyncMock(return_value="BACKWARD")
        self.set_compatibility = AsyncMock(return_value=None)


class MockEventBus:
    """Mock Event Bus"""

    def __init__(self):
        self.subscribe = MagicMock()
        self.events: list[tuple[str, Any]] = []

    async def publish(self, event_type: str, data: Any) -> None:
        """이벤트 발행 기록"""
        self.events.append((event_type, data))

    def get_events_by_type(self, event_type: str) -> list[Any]:
        """특정 타입의 이벤트 조회"""
        return [data for evt_type, data in self.events if evt_type == event_type]

    def clear_events(self) -> None:
        """이벤트 기록 초기화"""
        self.events.clear()


class MockRepository:
    """Mock Repository 베이스"""

    def __init__(self):
        self._storage: dict[Any, Any] = {}
        self._id_counter = 1

    async def create(self, entity: Any) -> Any:
        """엔티티 생성"""
        entity_id = self._id_counter
        self._id_counter += 1
        self._storage[entity_id] = entity
        return entity

    async def get_by_id(self, entity_id: Any) -> Any | None:
        """ID로 엔티티 조회"""
        return self._storage.get(entity_id)

    async def list_all(self) -> list[Any]:
        """모든 엔티티 조회"""
        return list(self._storage.values())

    async def update(self, entity_id: Any, entity: Any) -> Any | None:
        """엔티티 업데이트"""
        if entity_id in self._storage:
            self._storage[entity_id] = entity
            return entity
        return None

    async def delete(self, entity_id: Any) -> bool:
        """엔티티 삭제"""
        if entity_id in self._storage:
            del self._storage[entity_id]
            return True
        return False

    def clear(self) -> None:
        """저장소 초기화"""
        self._storage.clear()
        self._id_counter = 1


def create_mock_settings(overrides: dict[str, Any] | None = None) -> Any:
    """Mock Settings 객체 생성"""

    class MockDatabaseSettings:
        def __init__(self):
            self.host = "localhost"
            self.port = 3306
            self.username = "test"
            self.password = "test"
            self.database = "test_db"
            self.echo = False

        @property
        def url(self) -> str:
            return "sqlite+aiosqlite:///:memory:"

    class MockKafkaSettings:
        def __init__(self):
            self.bootstrap_servers = "localhost:9092"
            self.security_protocol = "PLAINTEXT"

        @property
        def admin_config(self) -> dict[str, Any]:
            return {
                "bootstrap.servers": self.bootstrap_servers,
                "security.protocol": self.security_protocol,
            }

    class MockSchemaRegistrySettings:
        def __init__(self):
            self.url = "http://localhost:8081"
            self.timeout = 30

        @property
        def client_config(self) -> dict[str, Any]:
            return {
                "url": self.url,
                "timeout": self.timeout,
            }

    class MockAppSettings:
        def __init__(self):
            self.app_name = "Test App"
            self.app_version = "0.0.1"
            self.debug = True
            self.environment = "development"
            self.database = MockDatabaseSettings()
            self.kafka = MockKafkaSettings()
            self.schema_registry = MockSchemaRegistrySettings()

    settings = MockAppSettings()

    # 오버라이드 적용
    if overrides:
        for key, value in overrides.items():
            if "." in key:
                # 중첩된 속성 처리 (예: "database.host")
                parts = key.split(".")
                obj = settings
                for part in parts[:-1]:
                    obj = getattr(obj, part)
                setattr(obj, parts[-1], value)
            else:
                setattr(settings, key, value)

    return settings
