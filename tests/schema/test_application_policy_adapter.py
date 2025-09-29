"""SchemaPolicyAdapter 단위 테스트"""

from app.policy.domain.models import DomainPolicySeverity, DomainPolicyViolation, DomainResourceType
from app.schema.application.policy_adapter import SchemaPolicyAdapter
from app.schema.domain.models import DomainPolicyViolation as SchemaViolation


class TestSchemaPolicyAdapter:
    """SchemaPolicyAdapter 테스트"""

    def test_to_policy_violation_warning(self):
        """WARNING severity 변환 테스트"""
        schema_violation = SchemaViolation(
            subject="dev.test-schema",
            rule="schema.naming.pattern",
            message="Invalid naming",
            severity="warning",
            field="subject",
        )

        policy_violation = SchemaPolicyAdapter.to_policy_violation(schema_violation)

        assert policy_violation.resource_type == DomainResourceType.SCHEMA
        assert policy_violation.resource_name == "dev.test-schema"
        assert policy_violation.rule_id == "schema.naming.pattern"
        assert policy_violation.message == "Invalid naming"
        assert policy_violation.severity == DomainPolicySeverity.WARNING
        assert policy_violation.field == "subject"

    def test_to_policy_violation_error_default(self):
        """ERROR severity 기본값 변환 테스트"""
        schema_violation = SchemaViolation(
            subject="dev.test-schema",
            rule="schema.naming.pattern",
            message="Invalid naming",
            severity="error",  # 명시적 error
            field="subject",
        )

        policy_violation = SchemaPolicyAdapter.to_policy_violation(schema_violation)

        assert policy_violation.severity == DomainPolicySeverity.ERROR

    def test_to_policy_violation_unknown_severity(self):
        """알 수 없는 severity 변환 테스트"""
        schema_violation = SchemaViolation(
            subject="dev.test-schema",
            rule="schema.naming.pattern",
            message="Invalid naming",
            severity="unknown",  # 알 수 없는 severity
            field="subject",
        )

        policy_violation = SchemaPolicyAdapter.to_policy_violation(schema_violation)

        # 기본값 ERROR로 매핑
        assert policy_violation.severity == DomainPolicySeverity.ERROR

    def test_from_policy_violation_roundtrip(self):
        """왕복 변환 테스트"""
        # PolicyViolation 생성
        policy_violation = DomainPolicyViolation(
            resource_type=DomainResourceType.SCHEMA,
            resource_name="dev.test-schema",
            rule_id="schema.naming.pattern",
            message="Invalid naming",
            severity=DomainPolicySeverity.WARNING,
            field="subject",
        )

        # SchemaViolation으로 변환
        schema_violation = SchemaPolicyAdapter.from_policy_violation(policy_violation)

        # 다시 PolicyViolation으로 변환
        policy_violation_back = SchemaPolicyAdapter.to_policy_violation(schema_violation)

        # 원본과 동일한지 확인
        assert policy_violation_back == policy_violation
