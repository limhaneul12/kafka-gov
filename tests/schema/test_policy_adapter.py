"""Schema Policy Adapter 테스트"""

from __future__ import annotations

from app.policy.domain.models import DomainPolicySeverity, DomainResourceType
from app.schema.application.policy_adapter import SchemaPolicyAdapter
from app.schema.domain.models import DomainPolicyViolation


class TestSchemaPolicyAdapter:
    """SchemaPolicyAdapter 테스트"""

    def test_to_policy_violation(self):
        """Schema violation을 Policy violation으로 변환"""
        schema_violation = DomainPolicyViolation(
            subject="dev.test-value",
            rule="schema.naming.pattern",
            message="Invalid naming pattern",
            severity="error",
            field="subject",
        )

        policy_violation = SchemaPolicyAdapter.to_policy_violation(schema_violation)

        assert policy_violation.resource_type == DomainResourceType.SCHEMA
        assert policy_violation.resource_name == "dev.test-value"
        assert policy_violation.rule_id == "schema.naming.pattern"
        assert policy_violation.message == "Invalid naming pattern"
        assert policy_violation.severity == DomainPolicySeverity.ERROR
        assert policy_violation.field == "subject"

    def test_to_policy_violation_with_warning(self):
        """Warning severity 변환"""
        schema_violation = DomainPolicyViolation(
            subject="dev.test-value",
            rule="schema.metadata.missing",
            message="Metadata missing",
            severity="warning",
        )

        policy_violation = SchemaPolicyAdapter.to_policy_violation(schema_violation)

        assert policy_violation.severity == DomainPolicySeverity.WARNING

    def test_from_policy_violation(self):
        """Policy violation을 Schema violation으로 변환"""
        from app.policy.domain.models import DomainPolicyViolation as PolicyViolation

        policy_violation = PolicyViolation(
            resource_type=DomainResourceType.SCHEMA,
            resource_name="dev.test-value",
            rule_id="schema.compatibility.mode",
            message="Incompatible mode",
            severity=DomainPolicySeverity.ERROR,
            field="compatibility",
        )

        schema_violation = SchemaPolicyAdapter.from_policy_violation(policy_violation)

        assert schema_violation.subject == "dev.test-value"
        assert schema_violation.rule == "schema.compatibility.mode"
        assert schema_violation.message == "Incompatible mode"
        assert schema_violation.severity == "error"
        assert schema_violation.field == "compatibility"

    def test_from_policy_violation_with_critical(self):
        """Critical severity 변환"""
        from app.policy.domain.models import DomainPolicyViolation as PolicyViolation

        policy_violation = PolicyViolation(
            resource_type=DomainResourceType.SCHEMA,
            resource_name="prod.critical-value",
            rule_id="schema.security.violation",
            message="Security violation",
            severity=DomainPolicySeverity.CRITICAL,
        )

        schema_violation = SchemaPolicyAdapter.from_policy_violation(policy_violation)

        assert schema_violation.severity == "critical"  # CRITICAL은 그대로 매핑
