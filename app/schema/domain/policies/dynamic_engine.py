"""Dynamic Schema Policy Engine"""

from __future__ import annotations

import json
from typing import Any

from app.schema.domain.models import DomainPolicyViolation, DomainSchemaSpec
from app.schema.domain.models.policy_management import DomainSchemaPolicy, SchemaPolicyType
from app.schema.domain.policies.documentation import SchemaDocPolicy
from app.schema.domain.policies.evolution import NullableDefaultPolicy
from app.schema.domain.policies.naming import FieldNamingPolicy
from app.schema.domain.policies.standards import NamespaceStandardPolicy


class DynamicSchemaPolicyEngine:
    """사용자 정의 정책을 기반으로 스키마 검증을 수행하는 엔진"""

    def __init__(self, policies: list[DomainSchemaPolicy]) -> None:
        self.policies = policies
        # 기존 하드코딩된 정책들의 인스턴스 (매핑용)
        self._policy_instances = {
            "MISSING_DOC": SchemaDocPolicy(),
            "NULLABLE_DEFAULT_MISSING": NullableDefaultPolicy(),
            "NAMESPACE_NOT_STANDARD": NamespaceStandardPolicy(),
            "NAMING_INCONSISTENT": FieldNamingPolicy(),
        }

    def evaluate(self, spec: DomainSchemaSpec, env: str) -> list[DomainPolicyViolation]:
        """스키마 스펙을 활성화된 정책들에 대해 검증"""
        all_violations: list[DomainPolicyViolation] = []

        if not spec.schema:
            return all_violations

        try:
            schema_dict = json.loads(spec.schema)
        except Exception:
            # 파싱 에러는 별도 처리 (여기서는 스킵하거나 에러 추가)
            return all_violations

        for policy in self.policies:
            # 1. 환경 체크 (total이거나 현재 환경과 일치하는 경우만)
            if policy.target_environment != "total" and policy.target_environment != env:
                continue

            # 2. 타입별 검증 수행
            if policy.policy_type == SchemaPolicyType.LINT:
                violations = self._evaluate_lint_policy(policy, spec.subject, schema_dict)
                all_violations.extend(violations)

            elif policy.policy_type == SchemaPolicyType.GUARDRAIL:
                violations = self._evaluate_guardrail_policy(policy, spec, env)
                all_violations.extend(violations)

        return all_violations

    def _evaluate_lint_policy(
        self, policy: DomainSchemaPolicy, subject: str, schema_dict: dict[str, Any]
    ) -> list[DomainPolicyViolation]:
        """LINT 타입 정책 검증 (내용 검사)"""
        violations: list[DomainPolicyViolation] = []
        rules_config = policy.content.get("rules", {})

        for rule_code, config in rules_config.items():
            if not config.get("enabled", True):
                continue

            instance = self._policy_instances.get(rule_code)
            if not instance:
                continue

            # 정책 실행
            lint_results = instance.check(schema_dict)

            for lr in lint_results:
                # 사용자 설정에 따른 Severity 덮어쓰기
                severity = config.get(
                    "severity", "error" if lr.severity == "ERROR" else "warning"
                ).lower()

                violations.append(
                    DomainPolicyViolation(
                        subject=subject,
                        rule=lr.code,
                        message=lr.rule + ": " + lr.actual,
                        severity=severity,
                        field=None,
                    )
                )

        return violations

    def _evaluate_guardrail_policy(
        self, policy: DomainSchemaPolicy, spec: DomainSchemaSpec, env: str
    ) -> list[DomainPolicyViolation]:
        """GUARDRAIL 타입 정책 검증 (운영 환경 제약 등)"""
        violations: list[DomainPolicyViolation] = []
        config = policy.content

        # 예: 호환성 모드 제약
        required_compat = config.get("required_compatibility")
        if required_compat:
            current_compat = (
                spec.compatibility.value
                if hasattr(spec.compatibility, "value")
                else spec.compatibility
            )
            if current_compat != required_compat:
                violations.append(
                    DomainPolicyViolation(
                        subject=spec.subject,
                        rule="GUARDRAIL_COMPATIBILITY",
                        message=f"호환성 모드 제약 위반: {required_compat}이(가) 필요하지만 {current_compat} 설정됨",
                        severity=config.get("severity", "error").lower(),
                    )
                )

        return violations
