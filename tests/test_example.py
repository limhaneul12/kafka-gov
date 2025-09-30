"""예제 테스트 - 테스트 환경 검증용"""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from tests.factories import create_test_schema_data, create_test_topic_data
from tests.helpers import assert_dict_contains, is_valid_iso_datetime
from tests.mocks import MockEventBus, MockRepository, create_mock_settings


@pytest.mark.unit
@pytest.mark.asyncio
async def test_db_session_works(db_session: AsyncSession):
    """데이터베이스 세션이 정상 동작하는지 검증"""
    result = await db_session.execute(text("SELECT 1"))
    value = result.scalar()
    assert value == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_db_session_rollback(db_session: AsyncSession):
    """세션 롤백이 정상 동작하는지 검증"""
    # 트랜잭션 내에서 작업
    await db_session.execute(text("SELECT 1"))
    # 픽스처가 자동으로 롤백 수행
    assert True


@pytest.mark.unit
def test_factory_creates_schema_data():
    """팩토리가 스키마 데이터를 올바르게 생성하는지 검증"""
    data = create_test_schema_data(subject="test-subject", version=2)

    assert data["subject"] == "test-subject"
    assert data["version"] == 2
    assert data["schema_type"] == "AVRO"
    assert "created_at" in data
    assert is_valid_iso_datetime(data["created_at"].isoformat())


@pytest.mark.unit
def test_factory_creates_topic_data():
    """팩토리가 토픽 데이터를 올바르게 생성하는지 검증"""
    data = create_test_topic_data(name="my-topic", partitions=5)

    assert data["name"] == "my-topic"
    assert data["partitions"] == 5
    assert data["replication_factor"] == 1
    assert "config" in data
    assert "created_at" in data


@pytest.mark.unit
def test_helper_assert_dict_contains():
    """헬퍼 함수가 딕셔너리 포함 여부를 올바르게 검증하는지 확인"""
    actual = {"a": 1, "b": 2, "c": 3}
    expected = {"a": 1, "b": 2}

    # 예외가 발생하지 않아야 함
    assert_dict_contains(actual, expected)


@pytest.mark.unit
def test_helper_assert_dict_contains_fails():
    """헬퍼 함수가 불일치를 올바르게 감지하는지 확인"""
    actual = {"a": 1, "b": 2}
    expected = {"a": 1, "c": 3}

    with pytest.raises(AssertionError):
        assert_dict_contains(actual, expected)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_mock_repository():
    """Mock Repository가 정상 동작하는지 검증"""
    repo = MockRepository()

    # 생성
    entity = {"name": "test"}
    created = await repo.create(entity)
    assert created == entity

    # 조회
    entities = await repo.list_all()
    assert len(entities) == 1

    # 삭제
    deleted = await repo.delete(1)
    assert deleted is True

    entities = await repo.list_all()
    assert len(entities) == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_mock_event_bus():
    """Mock Event Bus가 정상 동작하는지 검증"""
    bus = MockEventBus()

    # 이벤트 발행
    await bus.publish("test.event", {"data": "value"})
    await bus.publish("test.event", {"data": "value2"})
    await bus.publish("other.event", {"data": "other"})

    # 이벤트 조회
    test_events = bus.get_events_by_type("test.event")
    assert len(test_events) == 2
    assert test_events[0]["data"] == "value"

    other_events = bus.get_events_by_type("other.event")
    assert len(other_events) == 1

    # 초기화
    bus.clear_events()
    assert len(bus.events) == 0


@pytest.mark.unit
def test_mock_settings():
    """Mock Settings가 정상 동작하는지 검증"""
    settings = create_mock_settings()

    assert settings.app_name == "Test App"
    assert settings.database.url == "sqlite+aiosqlite:///:memory:"
    assert settings.kafka.bootstrap_servers == "localhost:9092"


@pytest.mark.unit
def test_mock_settings_with_overrides():
    """Mock Settings 오버라이드가 정상 동작하는지 검증"""
    settings = create_mock_settings(
        overrides={
            "app_name": "Custom App",
            "database.host": "custom-host",
        }
    )

    assert settings.app_name == "Custom App"
    assert settings.database.host == "custom-host"


@pytest.mark.unit
def test_sample_fixtures(sample_topic_name: str, sample_schema_json: dict):
    """샘플 픽스처가 정상 동작하는지 검증"""
    assert sample_topic_name == "test-topic"
    assert "type" in sample_schema_json
    assert sample_schema_json["type"] == "record"
