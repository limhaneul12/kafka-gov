"""Analysis Domain Models 테스트"""

from __future__ import annotations

import pytest

from app.analysis.domain.models import (
    SchemaImpactAnalysis,
    TopicSchemaCorrelation,
    TopicSchemaUsage,
)


class TestTopicSchemaCorrelation:
    """TopicSchemaCorrelation 테스트"""

    def test_create_correlation(self):
        """상관관계 생성"""
        corr = TopicSchemaCorrelation(
            correlation_id="corr_123",
            topic_name="dev.user.events",
            key_schema_subject="dev.user-key",
            value_schema_subject="dev.user-value",
            environment="dev",
            link_source="auto",
            confidence_score=0.9,
        )

        assert corr.correlation_id == "corr_123"
        assert corr.topic_name == "dev.user.events"
        assert corr.key_schema_subject == "dev.user-key"
        assert corr.value_schema_subject == "dev.user-value"

    def test_has_schema_with_both(self):
        """key와 value 스키마 모두 있음"""
        corr = TopicSchemaCorrelation(
            correlation_id="corr_123",
            topic_name="dev.test",
            key_schema_subject="dev.test-key",
            value_schema_subject="dev.test-value",
            environment="dev",
            link_source="auto",
            confidence_score=0.9,
        )

        assert corr.has_schema() is True

    def test_has_schema_with_key_only(self):
        """key 스키마만 있음"""
        corr = TopicSchemaCorrelation(
            correlation_id="corr_123",
            topic_name="dev.test",
            key_schema_subject="dev.test-key",
            value_schema_subject=None,
            environment="dev",
            link_source="auto",
            confidence_score=0.9,
        )

        assert corr.has_schema() is True

    def test_has_schema_with_value_only(self):
        """value 스키마만 있음"""
        corr = TopicSchemaCorrelation(
            correlation_id="corr_123",
            topic_name="dev.test",
            key_schema_subject=None,
            value_schema_subject="dev.test-value",
            environment="dev",
            link_source="auto",
            confidence_score=0.9,
        )

        assert corr.has_schema() is True

    def test_has_schema_with_none(self):
        """스키마 없음"""
        corr = TopicSchemaCorrelation(
            correlation_id="corr_123",
            topic_name="dev.test",
            key_schema_subject=None,
            value_schema_subject=None,
            environment="dev",
            link_source="manual",
            confidence_score=1.0,
        )

        assert corr.has_schema() is False

    def test_correlation_is_frozen(self):
        """상관관계는 불변"""
        corr = TopicSchemaCorrelation(
            correlation_id="corr_123",
            topic_name="dev.test",
            key_schema_subject=None,
            value_schema_subject=None,
            environment="dev",
            link_source="auto",
            confidence_score=0.9,
        )

        with pytest.raises(AttributeError):
            corr.topic_name = "new.topic"  # type: ignore[misc]


class TestSchemaImpactAnalysis:
    """SchemaImpactAnalysis 테스트"""

    def test_create_impact_analysis(self):
        """영향도 분석 생성"""
        analysis = SchemaImpactAnalysis(
            subject="prod.user-value",
            affected_topics=("prod.user.events", "prod.user.updates"),
            total_impact_count=2,
            risk_level="high",
            warnings=("프로덕션 스키마", "2개 토픽 영향"),
        )

        assert analysis.subject == "prod.user-value"
        assert len(analysis.affected_topics) == 2
        assert analysis.total_impact_count == 2
        assert analysis.risk_level == "high"

    def test_impact_is_frozen(self):
        """영향도 분석은 불변"""
        analysis = SchemaImpactAnalysis(
            subject="dev.test",
            affected_topics=(),
            total_impact_count=0,
            risk_level="low",
            warnings=(),
        )

        with pytest.raises(AttributeError):
            analysis.risk_level = "high"  # type: ignore[misc]


class TestTopicSchemaUsage:
    """TopicSchemaUsage 테스트"""

    def test_create_usage(self):
        """사용 현황 생성"""
        usage = TopicSchemaUsage(
            topic_name="dev.user.events",
            key_schema="dev.user-key",
            value_schema="dev.user-value",
            schema_versions={"key": 5, "value": 12},
            last_updated="2025-09-30T10:00:00Z",
        )

        assert usage.topic_name == "dev.user.events"
        assert usage.key_schema == "dev.user-key"
        assert usage.value_schema == "dev.user-value"
        assert usage.schema_versions["key"] == 5
        assert usage.schema_versions["value"] == 12

    def test_usage_is_frozen(self):
        """사용 현황은 불변"""
        usage = TopicSchemaUsage(
            topic_name="dev.test",
            key_schema=None,
            value_schema=None,
            schema_versions={},
            last_updated="2025-09-30T10:00:00Z",
        )

        with pytest.raises(AttributeError):
            usage.topic_name = "new.topic"  # type: ignore[misc]


class TestSchemaImpactAnalysisExtended:
    """SchemaImpactAnalysis 추가 테스트"""

    def test_analysis_with_multiple_topics(self):
        """여러 토픽에 영향"""
        analysis = SchemaImpactAnalysis(
            subject="dev.user-value",
            affected_topics=("dev.user.events", "dev.user.updates", "dev.user.deletes"),
            total_impact_count=3,
            risk_level="high",
            warnings=("Multiple topics affected", "High risk change"),
        )

        assert len(analysis.affected_topics) == 3
        assert analysis.total_impact_count == 3
        assert analysis.risk_level == "high"
        assert len(analysis.warnings) == 2

    def test_analysis_with_no_impact(self):
        """영향 없음"""
        analysis = SchemaImpactAnalysis(
            subject="dev.test-value",
            affected_topics=(),
            total_impact_count=0,
            risk_level="low",
            warnings=(),
        )

        assert len(analysis.affected_topics) == 0
        assert analysis.total_impact_count == 0
        assert analysis.risk_level == "low"

    def test_analysis_is_frozen(self):
        """분석 결과는 불변"""
        analysis = SchemaImpactAnalysis(
            subject="dev.test-value",
            affected_topics=(),
            total_impact_count=0,
            risk_level="low",
            warnings=(),
        )

        with pytest.raises(AttributeError):
            analysis.risk_level = "high"  # type: ignore[misc]
