"""Analysis Event Handlers 테스트"""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime
from unittest.mock import AsyncMock, Mock, call

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.analysis.application.event_handlers import (
    SchemaRegisteredHandler,
    TopicCreatedHandler,
)
from app.analysis.domain.services import TopicSchemaLinker
from app.shared.domain.events import SchemaRegisteredEvent, TopicCreatedEvent
from app.shared.roles import UserRole


@pytest.fixture
def mock_linker() -> TopicSchemaLinker:
    """Mock TopicSchemaLinker"""
    mock = AsyncMock(spec=TopicSchemaLinker)
    mock.link_schema_to_topic.return_value = None
    return mock


@pytest.fixture
def mock_session_factory() -> Mock:
    """Mock Session Factory"""

    @asynccontextmanager
    async def factory():
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.execute = AsyncMock()
        mock_session.flush = AsyncMock()
        mock_session.add = Mock()
        yield mock_session

    return Mock(return_value=factory())


class TestSchemaRegisteredHandler:
    """SchemaRegisteredHandler 테스트"""

    @pytest.mark.asyncio
    async def test_handle_with_topic_name_strategy_key(
        self, mock_linker: TopicSchemaLinker, mock_session_factory: Mock
    ) -> None:
        """TopicNameStrategy로 key 스키마 등록 처리"""
        # Given
        handler = SchemaRegisteredHandler(mock_linker, mock_session_factory)
        event = SchemaRegisteredEvent(
            event_id="evt_001",
            aggregate_id="change_001",
            occurred_at=datetime.now(),
            subject="user-events-key",
            version=1,
            schema_type="AVRO",
            schema_id=101,
            compatibility_mode="BACKWARD",
            subject_strategy="TopicNameStrategy",
            environment="dev",
            actor="admin@test.com",
            actor_role=UserRole.ADMIN.value,
        )

        # When
        await handler.handle(event)

        # Then
        mock_linker.link_schema_to_topic.assert_called_once_with(
            topic_name="user-events",
            schema_subject="user-events-key",
            schema_type="key",
            environment="dev",
            link_source="auto",
        )

    @pytest.mark.asyncio
    async def test_handle_with_topic_name_strategy_value(
        self, mock_linker: TopicSchemaLinker, mock_session_factory: Mock
    ) -> None:
        """TopicNameStrategy로 value 스키마 등록 처리"""
        # Given
        handler = SchemaRegisteredHandler(mock_linker, mock_session_factory)
        event = SchemaRegisteredEvent(
            event_id="evt_002",
            aggregate_id="change_002",
            occurred_at=datetime.now(),
            subject="order-events-value",
            version=2,
            schema_type="JSON",
            schema_id=102,
            compatibility_mode="FULL",
            subject_strategy="TopicNameStrategy",
            environment="stg",
            actor="developer@test.com",
            actor_role=UserRole.DEVELOPER.value,
        )

        # When
        await handler.handle(event)

        # Then
        mock_linker.link_schema_to_topic.assert_called_once_with(
            topic_name="order-events",
            schema_subject="order-events-value",
            schema_type="value",
            environment="stg",
            link_source="auto",
        )

    @pytest.mark.asyncio
    async def test_handle_with_topic_record_name_strategy(
        self, mock_linker: TopicSchemaLinker, mock_session_factory: Mock
    ) -> None:
        """TopicRecordNameStrategy로 스키마 등록 처리"""
        # Given
        handler = SchemaRegisteredHandler(mock_linker, mock_session_factory)
        event = SchemaRegisteredEvent(
            event_id="evt_003",
            aggregate_id="change_003",
            occurred_at=datetime.now(),
            subject="payments-PaymentCreated",
            version=1,
            schema_type="AVRO",
            schema_id=103,
            compatibility_mode="BACKWARD",
            subject_strategy="TopicRecordNameStrategy",
            environment="prod",
            actor="admin@test.com",
            actor_role=UserRole.ADMIN.value,
        )

        # When
        await handler.handle(event)

        # Then
        mock_linker.link_schema_to_topic.assert_called_once_with(
            topic_name="payments",
            schema_subject="payments-PaymentCreated",
            schema_type="value",
            environment="prod",
            link_source="auto",
        )

    @pytest.mark.asyncio
    async def test_handle_with_no_topics_inferred(
        self, mock_linker: TopicSchemaLinker, mock_session_factory: Mock
    ) -> None:
        """토픽을 추론할 수 없는 경우"""
        # Given
        handler = SchemaRegisteredHandler(mock_linker, mock_session_factory)
        event = SchemaRegisteredEvent(
            event_id="evt_004",
            aggregate_id="change_004",
            occurred_at=datetime.now(),
            subject="unknown-schema",
            version=1,
            schema_type="AVRO",
            schema_id=104,
            compatibility_mode="BACKWARD",
            subject_strategy="RecordNameStrategy",
            environment="dev",
            actor="admin@test.com",
            actor_role=UserRole.ADMIN.value,
        )

        # When
        await handler.handle(event)

        # Then
        mock_linker.link_schema_to_topic.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_with_no_permission(
        self, mock_linker: TopicSchemaLinker, mock_session_factory: Mock
    ) -> None:
        """권한이 없는 역할"""
        # Given
        handler = SchemaRegisteredHandler(mock_linker, mock_session_factory)
        event = SchemaRegisteredEvent(
            event_id="evt_005",
            aggregate_id="change_005",
            occurred_at=datetime.now(),
            subject="test-topic-value",
            version=1,
            schema_type="AVRO",
            schema_id=105,
            compatibility_mode="BACKWARD",
            subject_strategy="TopicNameStrategy",
            environment="dev",
            actor="viewer@test.com",
            actor_role=UserRole.VIEWER.value,
        )

        # When
        await handler.handle(event)

        # Then
        # VIEWER는 읽기 권한이 있으므로 링크는 호출됨
        mock_linker.link_schema_to_topic.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_exception_does_not_propagate(
        self, mock_linker: TopicSchemaLinker, mock_session_factory: Mock
    ) -> None:
        """예외가 발생해도 전파되지 않음 (베스트 에포트)"""
        # Given
        handler = SchemaRegisteredHandler(mock_linker, mock_session_factory)
        event = SchemaRegisteredEvent(
            event_id="evt_006",
            aggregate_id="change_006",
            occurred_at=datetime.now(),
            subject="error-topic-value",
            version=1,
            schema_type="AVRO",
            schema_id=106,
            compatibility_mode="BACKWARD",
            subject_strategy="TopicNameStrategy",
            environment="dev",
            actor="admin@test.com",
            actor_role=UserRole.ADMIN.value,
        )
        mock_linker.link_schema_to_topic.side_effect = Exception("Link failed")

        # When & Then (예외가 전파되지 않음)
        await handler.handle(event)

    def test_extract_topics_topic_name_strategy_key(
        self, mock_linker: TopicSchemaLinker, mock_session_factory: Mock
    ) -> None:
        """_extract_topics: TopicNameStrategy with -key suffix"""
        # Given
        handler = SchemaRegisteredHandler(mock_linker, mock_session_factory)

        # When
        topics = handler._extract_topics("user-events-key", "TopicNameStrategy")

        # Then
        assert topics == ["user-events"]

    def test_extract_topics_topic_name_strategy_value(
        self, mock_linker: TopicSchemaLinker, mock_session_factory: Mock
    ) -> None:
        """_extract_topics: TopicNameStrategy with -value suffix"""
        # Given
        handler = SchemaRegisteredHandler(mock_linker, mock_session_factory)

        # When
        topics = handler._extract_topics("order-events-value", "TopicNameStrategy")

        # Then
        assert topics == ["order-events"]

    def test_extract_topics_topic_record_name_strategy(
        self, mock_linker: TopicSchemaLinker, mock_session_factory: Mock
    ) -> None:
        """_extract_topics: TopicRecordNameStrategy"""
        # Given
        handler = SchemaRegisteredHandler(mock_linker, mock_session_factory)

        # When
        topics = handler._extract_topics("payments-PaymentCreated", "TopicRecordNameStrategy")

        # Then
        assert topics == ["payments"]

    def test_extract_topics_unknown_strategy(
        self, mock_linker: TopicSchemaLinker, mock_session_factory: Mock
    ) -> None:
        """_extract_topics: Unknown strategy"""
        # Given
        handler = SchemaRegisteredHandler(mock_linker, mock_session_factory)

        # When
        topics = handler._extract_topics("some-subject", "UnknownStrategy")

        # Then
        assert topics == []

    def test_infer_schema_type_key(
        self, mock_linker: TopicSchemaLinker, mock_session_factory: Mock
    ) -> None:
        """_infer_schema_type: -key suffix"""
        # Given
        handler = SchemaRegisteredHandler(mock_linker, mock_session_factory)

        # When
        schema_type = handler._infer_schema_type("user-events-key")

        # Then
        assert schema_type == "key"

    def test_infer_schema_type_value(
        self, mock_linker: TopicSchemaLinker, mock_session_factory: Mock
    ) -> None:
        """_infer_schema_type: -value suffix"""
        # Given
        handler = SchemaRegisteredHandler(mock_linker, mock_session_factory)

        # When
        schema_type = handler._infer_schema_type("order-events-value")

        # Then
        assert schema_type == "value"

    def test_infer_schema_type_default(
        self, mock_linker: TopicSchemaLinker, mock_session_factory: Mock
    ) -> None:
        """_infer_schema_type: 기본값 (value)"""
        # Given
        handler = SchemaRegisteredHandler(mock_linker, mock_session_factory)

        # When
        schema_type = handler._infer_schema_type("some-subject")

        # Then
        assert schema_type == "value"


class TestTopicCreatedHandler:
    """TopicCreatedHandler 테스트"""

    @pytest.mark.asyncio
    async def test_handle_topic_created(self, mock_linker: TopicSchemaLinker) -> None:
        """토픽 생성 이벤트 처리 (로깅만)"""
        # Given
        handler = TopicCreatedHandler(mock_linker)
        event = TopicCreatedEvent(
            event_id="evt_101",
            aggregate_id="change_101",
            occurred_at=datetime.now(),
            topic_name="user-events",
            partitions=3,
            replication_factor=2,
            environment="dev",
            actor="admin@test.com",
            actor_role=UserRole.ADMIN.value,
        )

        # When & Then (예외 없이 처리됨)
        await handler.handle(event)

    @pytest.mark.asyncio
    async def test_handle_exception_does_not_propagate(
        self, mock_linker: TopicSchemaLinker
    ) -> None:
        """예외가 발생해도 전파되지 않음"""
        # Given
        handler = TopicCreatedHandler(mock_linker)
        # 잘못된 이벤트 (필드 부족)
        event = TopicCreatedEvent(
            event_id="evt_102",
            aggregate_id="change_102",
            occurred_at=datetime.now(),
            topic_name="error-topic",
            partitions=3,
            replication_factor=2,
            environment="dev",
            actor="admin@test.com",
        )

        # When & Then (예외가 전파되지 않음)
        await handler.handle(event)
