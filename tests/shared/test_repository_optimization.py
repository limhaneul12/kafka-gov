"""Repository 최적화 테스트"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.shared.constants import ActivityType, AuditAction, AuditStatus
from app.shared.infrastructure.repository import (
    MySQLAuditActivityRepository,
    _get_models_to_query,
    _subquery_log_model,
)


class TestRepositoryOptimization:
    """Repository 쿼리 최적화 테스트"""

    @pytest.fixture
    def mock_session_factory(self):
        """Mock session factory"""

        async def _factory():
            session = AsyncMock()
            session.__aenter__ = AsyncMock(return_value=session)
            session.__aexit__ = AsyncMock(return_value=None)
            return session

        return _factory

    @pytest.fixture
    def repository(self, mock_session_factory):
        """테스트용 repository"""
        return MySQLAuditActivityRepository(mock_session_factory)

    async def test_get_recent_activities_uses_union_query(self, repository, mock_session_factory):
        """최근 활동 조회가 UNION 쿼리를 사용하는지 확인"""
        # Mock session setup
        session = await mock_session_factory()

        # Mock result
        mock_rows = [
            MagicMock(
                action=AuditAction.CREATE,
                target="test-topic",
                actor="test-user",
                timestamp=datetime.now(UTC),
                message="생성됨",
                snapshot={},
                activity_type=ActivityType.TOPIC,
            )
        ]

        mock_result = MagicMock()
        mock_result.fetchall.return_value = mock_rows
        session.execute = AsyncMock(return_value=mock_result)

        # Repository 교체
        repository.session_factory = lambda: session

        # 실행
        activities = await repository.get_recent_activities(limit=10)

        # 검증
        assert len(activities) <= 10
        assert session.execute.called
        # UNION 쿼리가 한 번만 실행되는지 확인
        assert session.execute.call_count == 1

    async def test_row_to_activity_conversion(self, repository):
        """Row to Activity 변환 테스트"""
        mock_row = MagicMock(
            action=AuditAction.CREATE,
            target="test-topic",
            actor="test-user",
            timestamp=datetime.now(UTC),
            message=None,  # 메시지가 None일 때 자동 포맷팅 확인
            snapshot={"test": "data"},
            activity_type=ActivityType.TOPIC,
        )

        activity = repository._row_to_activity(mock_row)

        assert activity.activity_type == ActivityType.TOPIC
        assert activity.action == AuditAction.CREATE
        assert activity.target == "test-topic"
        assert activity.actor == "test-user"
        assert activity.message == "생성됨"  # 자동 포맷팅 확인
        assert activity.metadata == {"test": "data"}

    async def test_build_filtered_query_with_all_filters(self, repository):
        """모든 필터가 적용된 쿼리 빌드 테스트"""
        from app.topic.infrastructure.models import AuditLogModel

        from_date = datetime.now(UTC) - timedelta(days=7)
        to_date = datetime.now(UTC)

        query = repository._build_filtered_query(
            model=AuditLogModel,
            activity_type=ActivityType.TOPIC,
            from_date=from_date,
            to_date=to_date,
            action=AuditAction.CREATE,
            actor="test-user",
            limit=100,
        )

        # 쿼리 객체가 생성되었는지 확인
        assert query is not None

    async def test_build_filtered_query_without_filters(self, repository):
        """필터 없는 쿼리 빌드 테스트"""
        from app.topic.infrastructure.models import AuditLogModel

        query = repository._build_filtered_query(
            model=AuditLogModel,
            activity_type=ActivityType.TOPIC,
            from_date=None,
            to_date=None,
            action=None,
            actor=None,
            limit=100,
        )

        # 쿼리 객체가 생성되었는지 확인
        assert query is not None


class TestSubqueryLogModel:
    """_subquery_log_model 헬퍼 함수 테스트"""

    def test_creates_select_query(self):
        """Select 쿼리 객체 생성 확인"""
        from app.topic.infrastructure.models import AuditLogModel

        query = _subquery_log_model(AuditLogModel, ActivityType.TOPIC)

        # SQLAlchemy Select 객체인지 확인
        assert query is not None
        assert hasattr(query, "where")
        assert hasattr(query, "limit")

    def test_includes_activity_type_label(self):
        """activity_type 라벨이 포함되는지 확인"""
        from app.topic.infrastructure.models import AuditLogModel

        query = _subquery_log_model(AuditLogModel, ActivityType.TOPIC)

        # 쿼리 문자열에 activity_type이 포함되어야 함
        query_str = str(query)
        assert "activity_type" in query_str.lower()

    def test_chainable_with_limit(self):
        """limit 체이닝 가능 확인"""
        from app.topic.infrastructure.models import AuditLogModel

        query = _subquery_log_model(AuditLogModel, ActivityType.TOPIC).limit(10)

        assert query is not None


class TestGetModelsToQuery:
    """_get_models_to_query 헬퍼 함수 테스트"""

    def test_no_filter_returns_both_models(self):
        """필터 없으면 Topic과 Schema 모두 반환"""
        from app.schema.infrastructure.models import SchemaAuditLogModel
        from app.topic.infrastructure.models import AuditLogModel

        models = _get_models_to_query(None)

        assert len(models) == 2
        assert (AuditLogModel, ActivityType.TOPIC) in models
        assert (SchemaAuditLogModel, ActivityType.SCHEMA) in models

    def test_topic_filter_returns_topic_only(self):
        """Topic 필터 시 Topic 모델만 반환"""
        from app.topic.infrastructure.models import AuditLogModel

        models = _get_models_to_query(ActivityType.TOPIC)

        assert len(models) == 1
        assert models[0] == (AuditLogModel, ActivityType.TOPIC)

    def test_schema_filter_returns_schema_only(self):
        """Schema 필터 시 Schema 모델만 반환"""
        from app.schema.infrastructure.models import SchemaAuditLogModel

        models = _get_models_to_query(ActivityType.SCHEMA)

        assert len(models) == 1
        assert models[0] == (SchemaAuditLogModel, ActivityType.SCHEMA)

    def test_unknown_filter_returns_empty(self):
        """알 수 없는 필터면 빈 리스트 반환"""
        models = _get_models_to_query("unknown")

        assert len(models) == 0
