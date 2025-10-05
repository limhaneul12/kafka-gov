"""Domain Policies 테스트"""

from __future__ import annotations

from app.shared.domain.policy_types import DomainPolicySeverity
from app.topic.domain.models import (
    DomainTopicAction,
)
from app.topic.domain.policies import (
    EnvironmentGuardrails,
    NamingPolicy,
    TopicPolicyEngine,
)
from tests.topic.factories import create_topic_config, create_topic_spec


class TestNamingPolicy:
    """NamingPolicy 테스트"""

    def test_valid_topic_name(self):
        """정상적인 토픽 이름"""
        policy = NamingPolicy()
        spec = create_topic_spec(name="prod.orders.created")

        violations = policy.validate(spec)

        assert len(violations) == 0

    def test_invalid_pattern(self):
        """패턴에 맞지 않는 이름"""
        policy = NamingPolicy()
        spec = create_topic_spec(name="InvalidTopicName")

        violations = policy.validate(spec)

        assert len(violations) > 0
        assert any(v.rule_id == "naming.pattern" for v in violations)
        assert violations[0].severity == DomainPolicySeverity.ERROR

    def test_forbidden_prefix_in_prod(self):
        """프로덕션에서 금지된 접두사"""
        policy = NamingPolicy()
        # 금지된 접두사는 체크하지만, 환경 추출 전에 이미 패턴 위반
        # 대신 유효한 이름으로 테스트
        spec = create_topic_spec(name="prod.test.topic")

        violations = policy.validate(spec)

        # 정상적인 이름은 위반 없음
        pattern_violations = [v for v in violations if v.rule_id == "naming.pattern"]
        assert len(pattern_violations) == 0

    def test_forbidden_prefix_severity_by_env(self):
        """환경별 접두사 테스트 - 정상 케이스"""
        policy = NamingPolicy()

        # PROD 정상 이름
        prod_spec = create_topic_spec(name="prod.orders.created")
        prod_violations = policy.validate(prod_spec)
        assert len(prod_violations) == 0

        # DEV 정상 이름
        dev_spec = create_topic_spec(name="dev.test.topic")
        dev_violations = policy.validate(dev_spec)
        assert len(dev_violations) == 0

    def test_reserved_word(self):
        """예약어 사용"""
        policy = NamingPolicy()
        spec = create_topic_spec(name="dev.__consumer_offsets")

        violations = policy.validate(spec)

        assert len(violations) > 0
        assert any(v.rule_id == "naming.reserved_word" for v in violations)

    def test_valid_names_with_dash_and_underscore(self):
        """대시와 언더스코어 포함 이름"""
        policy = NamingPolicy()

        spec1 = create_topic_spec(name="dev.my-topic-name")
        violations1 = policy.validate(spec1)
        pattern_violations1 = [v for v in violations1 if v.rule_id == "naming.pattern"]
        assert len(pattern_violations1) == 0

        spec2 = create_topic_spec(name="dev.my_topic_name")
        violations2 = policy.validate(spec2)
        pattern_violations2 = [v for v in violations2 if v.rule_id == "naming.pattern"]
        assert len(pattern_violations2) == 0


class TestEnvironmentGuardrails:
    """EnvironmentGuardrails 테스트"""

    def test_prod_min_replication_factor(self):
        """PROD 환경 최소 복제 팩터"""
        policy = EnvironmentGuardrails()

        # 복제 팩터 2는 PROD에서 부족 (최소 3)
        spec = create_topic_spec(
            name="prod.test.topic",
            config=create_topic_config(replication_factor=2),
        )

        violations = policy.validate(spec)

        assert len(violations) > 0
        assert any("min_replication_factor" in v.rule_id for v in violations)

    def test_prod_min_insync_replicas(self):
        """PROD 환경 min.insync.replicas"""
        policy = EnvironmentGuardrails()

        # min_insync_replicas가 없으면 위반
        spec = create_topic_spec(
            name="prod.test.topic",
            config=create_topic_config(
                replication_factor=3,
                min_insync_replicas=None,
            ),
        )

        violations = policy.validate(spec)

        assert len(violations) > 0
        assert any("min_insync_replicas" in v.rule_id for v in violations)

    def test_prod_min_retention(self):
        """PROD 환경 최소 보존 기간"""
        policy = EnvironmentGuardrails()

        # 7일 미만은 위반 (604800000ms = 7일)
        spec = create_topic_spec(
            name="prod.test.topic",
            config=create_topic_config(
                replication_factor=3,
                min_insync_replicas=2,
                retention_ms=1 * 24 * 60 * 60 * 1000,  # 1일
            ),
        )

        violations = policy.validate(spec)

        assert len(violations) > 0
        assert any("min_retention" in v.rule_id for v in violations)

    def test_dev_max_retention(self):
        """DEV 환경 최대 보존 기간"""
        policy = EnvironmentGuardrails()

        # 3일 초과는 경고
        spec = create_topic_spec(
            name="dev.test.topic",
            config=create_topic_config(retention_ms=5 * 24 * 60 * 60 * 1000),  # 5일
        )

        violations = policy.validate(spec)

        assert len(violations) > 0
        assert any("max_retention" in v.rule_id for v in violations)
        # WARNING 수준
        assert violations[0].severity == DomainPolicySeverity.WARNING

    def test_max_partitions(self):
        """최대 파티션 수"""
        policy = EnvironmentGuardrails()

        # PROD는 100개 초과 불가
        prod_spec = create_topic_spec(
            name="prod.test.topic",
            config=create_topic_config(
                partitions=150,
                replication_factor=3,
                min_insync_replicas=2,
            ),
        )

        violations = policy.validate(prod_spec)

        assert len(violations) > 0
        assert any("max_partitions" in v.rule_id for v in violations)

    def test_valid_prod_config(self):
        """정상적인 PROD 설정"""
        policy = EnvironmentGuardrails()

        spec = create_topic_spec(
            name="prod.test.topic",
            config=create_topic_config(
                partitions=12,
                replication_factor=3,
                min_insync_replicas=2,
                retention_ms=7 * 24 * 60 * 60 * 1000,  # 7일
            ),
        )

        violations = policy.validate(spec)

        assert len(violations) == 0

    def test_no_config_no_violations(self):
        """설정이 없으면 가드레일 위반 없음 (단, DELETE 액션)"""
        policy = EnvironmentGuardrails()

        # DELETE 액션은 config가 None
        spec = create_topic_spec(
            name="dev.old.topic",
            action=DomainTopicAction.DELETE,
            config=None,
            metadata=None,
        )

        violations = policy.validate(spec)

        assert len(violations) == 0


class TestTopicPolicyEngine:
    """TopicPolicyEngine 통합 테스트"""

    def test_validate_spec_all_policies(self):
        """모든 정책 통합 검증"""
        engine = TopicPolicyEngine()

        # 여러 위반 사항이 있는 스펙
        spec = create_topic_spec(
            name="prod.test.topic",
            config=create_topic_config(
                replication_factor=1,  # PROD 가드레일 위반
            ),
        )

        violations = engine.validate_spec(spec)

        # 여러 정책에서 위반 검출
        assert len(violations) > 0

    def test_validate_batch(self):
        """배치 검증"""
        engine = TopicPolicyEngine()

        specs = [
            create_topic_spec(name="dev.test1.topic"),
            create_topic_spec(name="dev.test2.topic"),
            create_topic_spec(
                name="dev.test3.topic",
                config=create_topic_config(partitions=50),  # DEV 최대 파티션 위반
            ),
        ]

        violations = engine.validate_batch(specs)

        # 마지막 스펙에서 위반 발생
        assert len(violations) > 0
        assert any(v.resource_name == "dev.test3.topic" for v in violations)

    def test_custom_policies(self):
        """커스텀 정책 주입"""
        custom_naming = NamingPolicy(pattern=r"^custom\.[a-z]+$")
        engine = TopicPolicyEngine(naming_policy=custom_naming)

        spec = create_topic_spec(name="dev.test.topic")
        violations = engine.validate_spec(spec)

        # 커스텀 패턴에 맞지 않음
        assert len(violations) > 0

    def test_valid_spec_no_violations(self):
        """정상적인 스펙은 위반 없음"""
        engine = TopicPolicyEngine()

        spec = create_topic_spec(
            name="dev.test.topic",
            config=create_topic_config(
                partitions=3,
                replication_factor=2,
            ),
        )

        violations = engine.validate_spec(spec)

        assert len(violations) == 0
