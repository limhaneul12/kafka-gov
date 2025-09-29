"""Schema와 Policy 모듈 간 DomainPolicyViolation 변환 어댑터"""

from __future__ import annotations

from typing import ClassVar

from app.policy.domain.models import (
    DomainPolicySeverity,
    DomainPolicyViolation as PolicyViolation,
    DomainResourceType,
)
from app.schema.domain.models import DomainPolicyViolation as SchemaViolation

PolicySeverityCategory = dict[str, DomainPolicySeverity]
PolicySeverityReverseCategory = dict[DomainPolicySeverity, str]


class SchemaPolicyAdapter:
    """스키마 정책 위반 ↔ 정책 모듈 위반 변환 어댑터"""

    # Severity 매핑 테이블 (대소문자 무시)
    _SEVERITY_MAP: ClassVar[PolicySeverityCategory] = {
        "warning": DomainPolicySeverity.WARNING,
        "error": DomainPolicySeverity.ERROR,
        "critical": DomainPolicySeverity.CRITICAL,
    }

    _REVERSE_SEVERITY_MAP: ClassVar[PolicySeverityReverseCategory] = {
        DomainPolicySeverity.WARNING: "warning",
        DomainPolicySeverity.ERROR: "error",
        DomainPolicySeverity.CRITICAL: "critical",
    }

    @classmethod
    def to_policy_violation(cls, schema_violation: SchemaViolation) -> PolicyViolation:
        """스키마 위반을 정책 위반으로 변환

        Args:
            schema_violation: 스키마 모듈의 DomainPolicyViolation

        Returns:
            정책 모듈의 DomainPolicyViolation
        """
        severity_enum = cls._SEVERITY_MAP.get(
            schema_violation.severity.lower(),
            DomainPolicySeverity.ERROR,  # 기본값
        )

        return PolicyViolation(
            resource_type=DomainResourceType.SCHEMA,
            resource_name=schema_violation.subject,
            rule_id=schema_violation.rule,
            message=schema_violation.message,
            severity=severity_enum,
            field=schema_violation.field,
        )

    @classmethod
    def from_policy_violation(cls, policy_violation: PolicyViolation) -> SchemaViolation:
        """정책 위반을 스키마 위반으로 변환

        Args:
            policy_violation: 정책 모듈의 DomainPolicyViolation

        Returns:
            스키마 모듈의 DomainPolicyViolation
        """
        severity_str = cls._REVERSE_SEVERITY_MAP.get(
            policy_violation.severity,
            "error",  # 기본값
        )

        return SchemaViolation(
            subject=policy_violation.resource_name,
            rule=policy_violation.rule_id,
            message=policy_violation.message,
            severity=severity_str,
            field=policy_violation.field,
        )
