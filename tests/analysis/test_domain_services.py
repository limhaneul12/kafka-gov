"""Analysis Domain Services 테스트"""

from __future__ import annotations

import pytest

from app.analysis.domain.models import TopicSchemaCorrelation
from app.analysis.domain.services import CorrelationAnalyzer, TopicSchemaLinker


class TestCorrelationAnalyzer:
    """CorrelationAnalyzer 테스트"""

    @pytest.mark.asyncio
    async def test_analyze_schema_impact_no_topics(self, mock_correlation_repository):
        """영향받는 토픽이 없는 경우"""
        analyzer = CorrelationAnalyzer(mock_correlation_repository)

        # Repository: 연결된 토픽 없음
        mock_correlation_repository.find_by_schema.return_value = []

        analysis = await analyzer.analyze_schema_impact(
            subject="dev.test-value",
            subject_strategy="TopicNameStrategy",
        )

        assert analysis.subject == "dev.test-value"
        assert analysis.risk_level in ("low", "medium")  # subject에서 토픽 추론 가능
        assert analysis.total_impact_count >= 0

    @pytest.mark.asyncio
    async def test_analyze_schema_impact_with_topics(self, mock_correlation_repository):
        """영향받는 토픽이 있는 경우"""
        analyzer = CorrelationAnalyzer(mock_correlation_repository)

        # Repository: 연결된 토픽 있음
        mock_correlation_repository.find_by_schema.return_value = [
            TopicSchemaCorrelation(
                correlation_id="corr_1",
                topic_name="dev.user.events",
                key_schema_subject=None,
                value_schema_subject="dev.test-value",
                environment="dev",
                link_source="auto",
                confidence_score=0.9,
            ),
            TopicSchemaCorrelation(
                correlation_id="corr_2",
                topic_name="dev.user.updates",
                key_schema_subject=None,
                value_schema_subject="dev.test-value",
                environment="dev",
                link_source="auto",
                confidence_score=0.9,
            ),
        ]

        analysis = await analyzer.analyze_schema_impact(
            subject="dev.test-value",
            subject_strategy="TopicNameStrategy",
        )

        assert analysis.subject == "dev.test-value"
        assert len(analysis.affected_topics) >= 2
        assert analysis.total_impact_count >= 2
        assert analysis.risk_level in ("low", "medium", "high")

    @pytest.mark.asyncio
    async def test_analyze_prod_schema_high_risk(self, mock_correlation_repository):
        """프로덕션 스키마는 high risk"""
        analyzer = CorrelationAnalyzer(mock_correlation_repository)

        mock_correlation_repository.find_by_schema.return_value = [
            TopicSchemaCorrelation(
                correlation_id="corr_1",
                topic_name="prod.user.events",
                key_schema_subject=None,
                value_schema_subject="prod.user-value",
                environment="prod",
                link_source="auto",
                confidence_score=0.9,
            ),
        ]

        analysis = await analyzer.analyze_schema_impact(
            subject="prod.user-value",
            subject_strategy="TopicNameStrategy",
        )

        assert analysis.risk_level == "high"
        assert any("프로덕션" in w for w in analysis.warnings)

    @pytest.mark.asyncio
    async def test_analyze_many_topics_high_risk(self, mock_correlation_repository):
        """많은 토픽에 영향 시 high risk"""
        analyzer = CorrelationAnalyzer(mock_correlation_repository)

        # 6개 토픽 (HIGH_RISK_TOPIC_THRESHOLD = 5)
        correlations = [
            TopicSchemaCorrelation(
                correlation_id=f"corr_{i}",
                topic_name=f"dev.topic{i}",
                key_schema_subject=None,
                value_schema_subject="dev.test-value",
                environment="dev",
                link_source="auto",
                confidence_score=0.9,
            )
            for i in range(6)
        ]
        mock_correlation_repository.find_by_schema.return_value = correlations

        analysis = await analyzer.analyze_schema_impact(
            subject="dev.test-value",
            subject_strategy="TopicNameStrategy",
        )

        assert analysis.risk_level == "high"
        assert analysis.total_impact_count >= 6


class TestTopicSchemaLinker:
    """TopicSchemaLinker 테스트"""

    @pytest.mark.asyncio
    async def test_link_new_key_schema(self, mock_correlation_repository):
        """새 토픽에 key 스키마 연결"""
        linker = TopicSchemaLinker(mock_correlation_repository)

        # Repository: 기존 연결 없음
        mock_correlation_repository.find_by_topic.return_value = None

        correlation = await linker.link_schema_to_topic(
            topic_name="dev.user.events",
            schema_subject="dev.user-key",
            schema_type="key",
            environment="dev",
            link_source="auto",
        )

        assert correlation.topic_name == "dev.user.events"
        assert correlation.key_schema_subject == "dev.user-key"
        assert correlation.value_schema_subject is None
        assert correlation.confidence_score == 0.9  # auto

        mock_correlation_repository.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_link_new_value_schema(self, mock_correlation_repository):
        """새 토픽에 value 스키마 연결"""
        linker = TopicSchemaLinker(mock_correlation_repository)

        mock_correlation_repository.find_by_topic.return_value = None

        correlation = await linker.link_schema_to_topic(
            topic_name="dev.user.events",
            schema_subject="dev.user-value",
            schema_type="value",
            environment="dev",
            link_source="manual",
        )

        assert correlation.topic_name == "dev.user.events"
        assert correlation.key_schema_subject is None
        assert correlation.value_schema_subject == "dev.user-value"
        assert correlation.confidence_score == 1.0  # manual

    @pytest.mark.asyncio
    async def test_update_existing_key_schema(self, mock_correlation_repository):
        """기존 연결에 key 스키마 업데이트"""
        linker = TopicSchemaLinker(mock_correlation_repository)

        # Repository: 기존 연결 있음 (value만)
        existing = TopicSchemaCorrelation(
            correlation_id="corr_123",
            topic_name="dev.user.events",
            key_schema_subject=None,
            value_schema_subject="dev.user-value",
            environment="dev",
            link_source="auto",
            confidence_score=0.9,
        )
        mock_correlation_repository.find_by_topic.return_value = existing

        correlation = await linker.link_schema_to_topic(
            topic_name="dev.user.events",
            schema_subject="dev.user-key",
            schema_type="key",
            environment="dev",
            link_source="auto",
        )

        assert correlation.correlation_id == "corr_123"  # 동일한 ID 유지
        assert correlation.key_schema_subject == "dev.user-key"  # key 추가
        assert correlation.value_schema_subject == "dev.user-value"  # value 유지

    @pytest.mark.asyncio
    async def test_update_existing_value_schema(self, mock_correlation_repository):
        """기존 연결에 value 스키마 업데이트"""
        linker = TopicSchemaLinker(mock_correlation_repository)

        # Repository: 기존 연결 있음 (key만)
        existing = TopicSchemaCorrelation(
            correlation_id="corr_123",
            topic_name="dev.user.events",
            key_schema_subject="dev.user-key",
            value_schema_subject=None,
            environment="dev",
            link_source="auto",
            confidence_score=0.9,
        )
        mock_correlation_repository.find_by_topic.return_value = existing

        correlation = await linker.link_schema_to_topic(
            topic_name="dev.user.events",
            schema_subject="dev.user-value",
            schema_type="value",
            environment="dev",
            link_source="manual",
        )

        assert correlation.correlation_id == "corr_123"
        assert correlation.key_schema_subject == "dev.user-key"  # key 유지
        assert correlation.value_schema_subject == "dev.user-value"  # value 추가
        assert correlation.confidence_score == 1.0  # manual
