"""Policy Integration 테스트"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.policy.domain.models import (
    DomainEnvironment,
    DomainPolicySeverity,
    DomainPolicyViolation,
    DomainResourceType,
)
from app.topic.application.policy_integration import TopicPolicyAdapter
from app.topic.domain.models import DomainTopicAction
from tests.topic.factories import create_topic_config, create_topic_spec


class TestTopicPolicyAdapter:
    """TopicPolicyAdapter 테스트"""

    @pytest.mark.asyncio
    async def test_validate_topic_specs(self):
        """토픽 스펙 검증"""
        mock_policy_service = AsyncMock()
        adapter = TopicPolicyAdapter(mock_policy_service)

        # 정책 서비스가 위반 반환
        violation = DomainPolicyViolation(
            resource_type=DomainResourceType.TOPIC,
            resource_name="dev.test.topic",
            rule_id="test.rule",
            message="Test violation",
            severity=DomainPolicySeverity.WARNING,
            field="name",
        )
        mock_policy_service.evaluate_batch.return_value = [violation]

        specs = [create_topic_spec(name="dev.test.topic")]
        violations = await adapter.validate_topic_specs(
            environment=DomainEnvironment.DEV,
            topic_specs=specs,
            actor="test-user",
        )

        assert len(violations) == 1
        assert violations[0].message == "Test violation"

        # PolicyTarget으로 변환되었는지 확인
        mock_policy_service.evaluate_batch.assert_called_once()
        call_args = mock_policy_service.evaluate_batch.call_args
        assert call_args.kwargs["environment"] == DomainEnvironment.DEV
        assert call_args.kwargs["resource_type"] == DomainResourceType.TOPIC
        assert len(call_args.kwargs["targets"]) == 1

    @pytest.mark.asyncio
    async def test_validate_single_topic(self):
        """단일 토픽 검증"""
        mock_policy_service = AsyncMock()
        adapter = TopicPolicyAdapter(mock_policy_service)

        mock_policy_service.evaluate_batch.return_value = []

        spec = create_topic_spec(name="dev.test.topic")
        violations = await adapter.validate_single_topic(
            environment=DomainEnvironment.DEV,
            topic_spec=spec,
            actor="test-user",
        )

        assert len(violations) == 0
        mock_policy_service.evaluate_batch.assert_called_once()

    def test_convert_topic_spec_to_policy_target(self):
        """TopicSpec을 PolicyTarget으로 변환"""
        mock_policy_service = AsyncMock()
        adapter = TopicPolicyAdapter(mock_policy_service)

        spec = create_topic_spec(
            name="dev.test.topic",
            config=create_topic_config(
                partitions=6,
                replication_factor=2,
                retention_ms=86400000,
            ),
        )

        target = adapter._convert_topic_spec_to_policy_target(spec)

        assert target["name"] == "dev.test.topic"
        assert target["config"]["partitions"] == "6"
        assert target["config"]["replication.factor"] == "2"
        assert target["config"]["retention.ms"] == "86400000"
        assert target["metadata"]["owner"] == "team-test"

    def test_convert_spec_without_config(self):
        """설정이 없는 스펙 변환 (DELETE 액션)"""
        mock_policy_service = AsyncMock()
        adapter = TopicPolicyAdapter(mock_policy_service)

        # DELETE 액션은 config가 None
        spec = create_topic_spec(
            name="dev.test.topic",
            action=DomainTopicAction.DELETE,
            config=None,
            metadata=None,
            reason="Clean up",
        )

        target = adapter._convert_topic_spec_to_policy_target(spec)

        assert target["name"] == "dev.test.topic"
        assert target["config"] == {}
        assert target["metadata"] == {}

    def test_has_blocking_violations(self):
        """차단 위반 확인"""
        from unittest.mock import Mock

        mock_policy_service = Mock()  # AsyncMock 대신 Mock 사용
        mock_policy_service.has_blocking_violations.return_value = True

        adapter = TopicPolicyAdapter(mock_policy_service)

        violations = [
            DomainPolicyViolation(
                resource_type=DomainResourceType.TOPIC,
                resource_name="dev.test.topic",
                rule_id="critical.rule",
                message="Critical",
                severity=DomainPolicySeverity.ERROR,
                field="name",
            )
        ]

        result = adapter.has_blocking_violations(violations)

        assert result is True
        mock_policy_service.has_blocking_violations.assert_called_once_with(violations)

    @pytest.mark.asyncio
    async def test_validate_multiple_specs(self):
        """여러 스펙 검증"""
        mock_policy_service = AsyncMock()
        adapter = TopicPolicyAdapter(mock_policy_service)

        mock_policy_service.evaluate_batch.return_value = []

        specs = [
            create_topic_spec(name="dev.test1.topic"),
            create_topic_spec(name="dev.test2.topic"),
            create_topic_spec(name="dev.test3.topic"),
        ]

        violations = await adapter.validate_topic_specs(
            environment=DomainEnvironment.DEV,
            topic_specs=specs,
            actor="test-user",
        )

        assert len(violations) == 0

        # 3개의 PolicyTarget이 전달되었는지 확인
        call_args = mock_policy_service.evaluate_batch.call_args
        assert len(call_args.kwargs["targets"]) == 3
