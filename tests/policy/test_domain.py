"""Policy 도메인 모델 테스트"""

from __future__ import annotations

import pytest

from app.policy.domain.models import (
    DomainConfigurationRule,
    DomainEnvironment,
    DomainNamingRule,
    DomainPolicyContext,
    DomainPolicySet,
    DomainPolicySeverity,
    DomainPolicyViolation,
    DomainResourceType,
    PolicyEngine,
)


class TestPolicyViolation:
    """PolicyViolation 테스트"""

    @pytest.mark.unit
    def test_should_create_policy_violation_with_required_fields(self) -> None:
        """필수 필드로 정책 위반을 생성해야 한다."""
        # Arrange & Act
        violation = DomainPolicyViolation(
            resource_type=DomainResourceType.TOPIC,
            resource_name="test-topic",
            rule_id="naming.pattern",
            message="Name does not match pattern",
            severity=DomainPolicySeverity.ERROR,
        )

        # Assert
        assert violation.resource_type == DomainResourceType.TOPIC
        assert violation.resource_name == "test-topic"
        assert violation.rule_id == "naming.pattern"
        assert violation.message == "Name does not match pattern"
        assert violation.severity == DomainPolicySeverity.ERROR
        assert violation.field is None
        assert violation.current_value is None
        assert violation.expected_value is None

    @pytest.mark.unit
    def test_should_create_policy_violation_with_optional_fields(self) -> None:
        """선택적 필드를 포함하여 정책 위반을 생성해야 한다."""
        # Arrange & Act
        violation = DomainPolicyViolation(
            resource_type=DomainResourceType.TOPIC,
            resource_name="test-topic",
            rule_id="config.partitions",
            message="Partition count is too low",
            severity=DomainPolicySeverity.WARNING,
            field="config.partitions",
            current_value=1,
            expected_value=">= 3",
        )

        # Assert
        assert violation.field == "config.partitions"
        assert violation.current_value == 1
        assert violation.expected_value == ">= 3"


class TestPolicyContext:
    """PolicyContext 테스트"""

    @pytest.mark.unit
    def test_should_create_policy_context_with_required_fields(self) -> None:
        """필수 필드로 정책 컨텍스트를 생성해야 한다."""
        # Arrange & Act
        context = DomainPolicyContext(
            environment=DomainEnvironment.PROD,
            resource_type=DomainResourceType.TOPIC,
            actor="test-user",
        )

        # Assert
        assert context.environment == DomainEnvironment.PROD
        assert context.resource_type == DomainResourceType.TOPIC
        assert context.actor == "test-user"
        assert context.metadata is None

    @pytest.mark.unit
    def test_should_create_policy_context_with_metadata(self) -> None:
        """메타데이터를 포함하여 정책 컨텍스트를 생성해야 한다."""
        # Arrange
        metadata = {"team": "data-platform", "project": "kafka-gov"}

        # Act
        context = DomainPolicyContext(
            environment=DomainEnvironment.DEV,
            resource_type=DomainResourceType.SCHEMA,
            actor="test-user",
            metadata=metadata,
        )

        # Assert
        assert context.metadata == metadata


class TestNamingRule:
    """NamingRule 테스트"""

    @pytest.fixture
    def naming_rule(self) -> DomainNamingRule:
        """기본 네이밍 규칙 픽스처"""
        return DomainNamingRule(
            pattern=r"^[a-z][a-z0-9-]*[a-z0-9]$",
            forbidden_prefixes=("test-", "tmp-"),
            forbidden_suffixes=("-temp", "-old"),
        )

    @pytest.fixture
    def policy_context(self) -> DomainPolicyContext:
        """정책 컨텍스트 픽스처"""
        return DomainPolicyContext(
            environment=DomainEnvironment.PROD,
            resource_type=DomainResourceType.TOPIC,
            actor="test-user",
        )

    @pytest.mark.unit
    def test_should_have_correct_rule_properties(self, naming_rule: DomainNamingRule) -> None:
        """올바른 규칙 속성을 가져야 한다."""
        # Assert
        assert naming_rule.rule_id == "naming.pattern"
        assert "pattern" in naming_rule.description
        assert naming_rule.pattern in naming_rule.description

    @pytest.mark.unit
    def test_should_pass_validation_for_valid_topic_name(
        self, naming_rule: DomainNamingRule, policy_context: DomainPolicyContext
    ) -> None:
        """유효한 토픽명에 대해 검증을 통과해야 한다."""
        # Arrange
        target = {"name": "user-events"}

        # Act
        violations = naming_rule.validate(target, policy_context)

        # Assert
        assert len(violations) == 0

    @pytest.mark.unit
    def test_should_fail_validation_for_invalid_pattern(
        self, naming_rule: DomainNamingRule, policy_context: DomainPolicyContext
    ) -> None:
        """잘못된 패턴의 토픽명에 대해 검증을 실패해야 한다."""
        # Arrange
        target = {"name": "UserEvents"}  # 대문자 포함

        # Act
        violations = naming_rule.validate(target, policy_context)

        # Assert
        assert len(violations) == 1
        violation = violations[0]
        assert violation.rule_id == "naming.pattern"
        assert violation.severity == DomainPolicySeverity.ERROR
        assert violation.field == "name"
        assert violation.current_value == "UserEvents"

    @pytest.mark.unit
    def test_should_fail_validation_for_forbidden_prefix_in_prod(
        self, naming_rule: DomainNamingRule
    ) -> None:
        """PROD 환경에서 금지된 접두사에 대해 검증을 실패해야 한다."""
        # Arrange
        target = {"name": "test-topic"}
        context = DomainPolicyContext(
            environment=DomainEnvironment.PROD,
            resource_type=DomainResourceType.TOPIC,
            actor="test-user",
        )

        # Act
        violations = naming_rule.validate(target, context)

        # Assert
        assert len(violations) == 1  # forbidden prefix 위반
        violation = violations[0]
        assert violation.rule_id == "naming.forbidden_prefix"
        assert "test-" in violation.message

    @pytest.mark.unit
    def test_should_pass_validation_for_forbidden_prefix_in_dev(
        self, naming_rule: DomainNamingRule
    ) -> None:
        """DEV 환경에서는 금지된 접두사를 허용해야 한다."""
        # Arrange
        target = {"name": "test-topic"}
        context = DomainPolicyContext(
            environment=DomainEnvironment.DEV,
            resource_type=DomainResourceType.TOPIC,
            actor="test-user",
        )

        # Act
        violations = naming_rule.validate(target, context)

        # Assert
        assert len(violations) == 0

    @pytest.mark.unit
    def test_should_extract_schema_subject_name(self, naming_rule: DomainNamingRule) -> None:
        """스키마 대상에서 subject 이름을 추출해야 한다."""
        # Arrange
        target = {"subject": "user-events-value"}
        context = DomainPolicyContext(
            environment=DomainEnvironment.PROD,
            resource_type=DomainResourceType.SCHEMA,
            actor="test-user",
        )

        # Act
        violations = naming_rule.validate(target, context)

        # Assert
        assert len(violations) == 0  # 유효한 스키마 이름


class TestConfigurationRule:
    """ConfigurationRule 테스트"""

    @pytest.fixture
    def partition_rule(self) -> DomainConfigurationRule:
        """파티션 설정 규칙 픽스처"""
        return DomainConfigurationRule(
            config_key="partitions",
            min_value=3,
            max_value=100,
            required=True,
        )

    @pytest.fixture
    def replication_rule(self) -> DomainConfigurationRule:
        """복제본 설정 규칙 픽스처"""
        return DomainConfigurationRule(
            config_key="replication.factor",
            allowed_values=(1, 3, 5),
            required=True,
        )

    @pytest.fixture
    def policy_context(self) -> DomainPolicyContext:
        """정책 컨텍스트 픽스처"""
        return DomainPolicyContext(
            environment=DomainEnvironment.PROD,
            resource_type=DomainResourceType.TOPIC,
            actor="test-user",
        )

    @pytest.mark.unit
    def test_should_have_correct_rule_properties(
        self, partition_rule: DomainConfigurationRule
    ) -> None:
        """올바른 규칙 속성을 가져야 한다."""
        # Assert
        assert partition_rule.rule_id == "config.partitions"
        assert "partitions" in partition_rule.description
        assert "required" in partition_rule.description
        assert "min=3" in partition_rule.description
        assert "max=100" in partition_rule.description

    @pytest.mark.unit
    def test_should_pass_validation_for_valid_config(
        self, partition_rule: DomainConfigurationRule, policy_context: DomainPolicyContext
    ) -> None:
        """유효한 설정에 대해 검증을 통과해야 한다."""
        # Arrange
        target = {"name": "test-topic", "config": {"partitions": 10}}

        # Act
        violations = partition_rule.validate(target, policy_context)

        # Assert
        assert len(violations) == 0

    @pytest.mark.unit
    def test_should_fail_validation_for_missing_required_config(
        self, partition_rule: DomainConfigurationRule, policy_context: DomainPolicyContext
    ) -> None:
        """필수 설정이 누락된 경우 검증을 실패해야 한다."""
        # Arrange
        target = {"name": "test-topic", "config": {}}

        # Act
        violations = partition_rule.validate(target, policy_context)

        # Assert
        assert len(violations) == 1
        violation = violations[0]
        assert violation.rule_id == "config.partitions"
        assert "Required config" in violation.message
        assert violation.severity == DomainPolicySeverity.ERROR

    @pytest.mark.unit
    def test_should_fail_validation_for_value_below_minimum(
        self, partition_rule: DomainConfigurationRule, policy_context: DomainPolicyContext
    ) -> None:
        """최솟값 미만의 값에 대해 검증을 실패해야 한다."""
        # Arrange
        target = {"name": "test-topic", "config": {"partitions": 1}}

        # Act
        violations = partition_rule.validate(target, policy_context)

        # Assert
        assert len(violations) == 1
        violation = violations[0]
        assert "below minimum" in violation.message
        assert violation.current_value == 1
        assert violation.expected_value == ">= 3"

    @pytest.mark.unit
    def test_should_fail_validation_for_value_above_maximum(
        self, partition_rule: DomainConfigurationRule, policy_context: DomainPolicyContext
    ) -> None:
        """최댓값 초과의 값에 대해 검증을 실패해야 한다."""
        # Arrange
        target = {"name": "test-topic", "config": {"partitions": 200}}

        # Act
        violations = partition_rule.validate(target, policy_context)

        # Assert
        assert len(violations) == 1
        violation = violations[0]
        assert "exceeds maximum" in violation.message
        assert violation.current_value == 200
        assert violation.expected_value == "<= 100"

    @pytest.mark.unit
    def test_should_fail_validation_for_disallowed_value(
        self, replication_rule: DomainConfigurationRule, policy_context: DomainPolicyContext
    ) -> None:
        """허용되지 않은 값에 대해 검증을 실패해야 한다."""
        # Arrange
        target = {"name": "test-topic", "config": {"replication.factor": 2}}

        # Act
        violations = replication_rule.validate(target, policy_context)

        # Assert
        assert len(violations) == 1
        violation = violations[0]
        assert "not allowed" in violation.message
        assert violation.current_value == 2
        assert violation.expected_value == [1, 3, 5]


class TestPolicySet:
    """PolicySet 테스트"""

    @pytest.fixture
    def naming_rule(self) -> DomainNamingRule:
        """네이밍 규칙 픽스처"""
        return DomainNamingRule(pattern=r"^[a-z][a-z0-9-]*[a-z0-9]$")

    @pytest.fixture
    def partition_rule(self) -> DomainConfigurationRule:
        """파티션 규칙 픽스처"""
        return DomainConfigurationRule(
            config_key="partitions",
            min_value=3,
            required=True,
        )

    @pytest.fixture
    def policy_set(
        self, naming_rule: DomainNamingRule, partition_rule: DomainConfigurationRule
    ) -> DomainPolicySet:
        """정책 집합 픽스처"""
        return DomainPolicySet(
            environment=DomainEnvironment.PROD,
            resource_type=DomainResourceType.TOPIC,
            rules=(naming_rule, partition_rule),
        )

    @pytest.mark.unit
    def test_should_create_policy_set_with_rules(self, policy_set: DomainPolicySet) -> None:
        """규칙들과 함께 정책 집합을 생성해야 한다."""
        # Assert
        assert policy_set.environment == DomainEnvironment.PROD
        assert policy_set.resource_type == DomainResourceType.TOPIC
        assert len(policy_set.rules) == 2

    @pytest.mark.unit
    def test_should_validate_batch_targets(self, policy_set: DomainPolicySet) -> None:
        """배치 대상들을 검증해야 한다."""
        # Arrange
        targets = [
            {"name": "user-events", "config": {"partitions": 5}},  # 유효
            {"name": "InvalidName", "config": {"partitions": 10}},  # 네이밍 위반
            {"name": "order-events", "config": {"partitions": 1}},  # 파티션 위반
        ]

        # Act
        violations = policy_set.validate_batch(targets, "test-user")

        # Assert
        assert len(violations) == 2  # 2개의 위반
        violation_rules = {v.rule_id for v in violations}
        assert "naming.pattern" in violation_rules
        assert "config.partitions" in violation_rules

    @pytest.mark.unit
    def test_should_pass_validation_for_valid_targets(self, policy_set: DomainPolicySet) -> None:
        """유효한 대상들에 대해 검증을 통과해야 한다."""
        # Arrange
        targets = [
            {"name": "user-events", "config": {"partitions": 5}},
            {"name": "order-events", "config": {"partitions": 10}},
        ]

        # Act
        violations = policy_set.validate_batch(targets, "test-user")

        # Assert
        assert len(violations) == 0


class TestPolicyEngine:
    """PolicyEngine 테스트"""

    @pytest.fixture
    def policy_engine(self) -> PolicyEngine:
        """정책 엔진 픽스처"""
        return PolicyEngine()

    @pytest.fixture
    def topic_policy_set(self) -> DomainPolicySet:
        """토픽 정책 집합 픽스처"""
        naming_rule = DomainNamingRule(pattern=r"^[a-z][a-z0-9-]*[a-z0-9]$")
        return DomainPolicySet(
            environment=DomainEnvironment.PROD,
            resource_type=DomainResourceType.TOPIC,
            rules=(naming_rule,),
        )

    @pytest.fixture
    def schema_policy_set(self) -> DomainPolicySet:
        """스키마 정책 집합 픽스처"""
        naming_rule = DomainNamingRule(pattern=r"^[a-z][a-z0-9-]*-(key|value)$")
        return DomainPolicySet(
            environment=DomainEnvironment.PROD,
            resource_type=DomainResourceType.SCHEMA,
            rules=(naming_rule,),
        )

    @pytest.mark.unit
    def test_should_register_policy_set(
        self, policy_engine: PolicyEngine, topic_policy_set: DomainPolicySet
    ) -> None:
        """정책 집합을 등록해야 한다."""
        # Act
        policy_engine.register_policy_set(topic_policy_set)

        # Assert
        retrieved = policy_engine.get_policy_set(DomainEnvironment.PROD, DomainResourceType.TOPIC)
        assert retrieved == topic_policy_set

    @pytest.mark.unit
    def test_should_evaluate_policies_for_registered_set(
        self, policy_engine: PolicyEngine, topic_policy_set: DomainPolicySet
    ) -> None:
        """등록된 정책 집합에 대해 정책을 평가해야 한다."""
        # Arrange
        policy_engine.register_policy_set(topic_policy_set)
        targets = [{"name": "InvalidName"}]  # 네이밍 위반

        # Act
        violations = policy_engine.evaluate(
            DomainEnvironment.PROD, DomainResourceType.TOPIC, targets, "test-user"
        )

        # Assert
        assert len(violations) == 1
        assert violations[0].rule_id == "naming.pattern"

    @pytest.mark.unit
    def test_should_return_empty_violations_for_unregistered_policy(
        self, policy_engine: PolicyEngine
    ) -> None:
        """등록되지 않은 정책에 대해 빈 위반 목록을 반환해야 한다."""
        # Arrange
        targets = [{"name": "any-name"}]

        # Act
        violations = policy_engine.evaluate(
            DomainEnvironment.DEV, DomainResourceType.TOPIC, targets, "test-user"
        )

        # Assert
        assert len(violations) == 0

    @pytest.mark.unit
    def test_should_list_environments(
        self,
        policy_engine: PolicyEngine,
        topic_policy_set: DomainPolicySet,
        schema_policy_set: DomainPolicySet,
    ) -> None:
        """등록된 환경 목록을 반환해야 한다."""
        # Arrange
        policy_engine.register_policy_set(topic_policy_set)
        policy_engine.register_policy_set(schema_policy_set)

        # Act
        environments = policy_engine.list_environments()

        # Assert
        assert DomainEnvironment.PROD in environments
        assert len(environments) == 1  # 둘 다 PROD 환경

    @pytest.mark.unit
    def test_should_list_resource_types_for_environment(
        self,
        policy_engine: PolicyEngine,
        topic_policy_set: DomainPolicySet,
        schema_policy_set: DomainPolicySet,
    ) -> None:
        """환경별 리소스 타입 목록을 반환해야 한다."""
        # Arrange
        policy_engine.register_policy_set(topic_policy_set)
        policy_engine.register_policy_set(schema_policy_set)

        # Act
        resource_types = policy_engine.list_resource_types(DomainEnvironment.PROD)

        # Assert
        assert DomainResourceType.TOPIC in resource_types
        assert DomainResourceType.SCHEMA in resource_types
        assert len(resource_types) == 2

    @pytest.mark.unit
    def test_should_handle_multiple_environments(self, policy_engine: PolicyEngine) -> None:
        """여러 환경을 처리해야 한다."""
        # Arrange
        dev_policy = DomainPolicySet(
            environment=DomainEnvironment.DEV,
            resource_type=DomainResourceType.TOPIC,
            rules=(),
        )
        prod_policy = DomainPolicySet(
            environment=DomainEnvironment.PROD,
            resource_type=DomainResourceType.TOPIC,
            rules=(),
        )

        policy_engine.register_policy_set(dev_policy)
        policy_engine.register_policy_set(prod_policy)

        # Act
        environments = policy_engine.list_environments()

        # Assert
        assert len(environments) == 2
        assert DomainEnvironment.DEV in environments
        assert DomainEnvironment.PROD in environments
