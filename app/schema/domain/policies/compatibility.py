"""Compatibility Policies"""

from app.schema.domain.models.policy import DomainPolicyViolation
from app.schema.domain.models.types_enum import DomainCompatibilityMode, DomainEnvironment


class CompatibilityGuardrail:
    """환경별 호환성 모드 제약 정책"""

    def check(
        self, subject: str, compatibility: DomainCompatibilityMode, env: DomainEnvironment
    ) -> list[DomainPolicyViolation]:
        """환경에 따른 최소 호환성 레벨 검사"""
        violations: list[DomainPolicyViolation] = []

        # 1. 운영(PROD) 환경은 최소 FULL 호환성 권장/강제
        if env == DomainEnvironment.PROD:
            if compatibility not in [
                DomainCompatibilityMode.FULL,
                DomainCompatibilityMode.FULL_TRANSITIVE,
            ]:
                violations.append(
                    DomainPolicyViolation(
                        subject=subject,
                        rule="PROD_COMPAT_RESTRICTION",
                        message="운영(PROD) 환경의 스키마는 FULL 또는 FULL_TRANSITIVE 호환성 모드가 필요합니다.",
                        severity="error",
                    )
                )

        # 2. 스테이징(STG) 환경은 최소 BACKWARD 이상 권장
        elif env == DomainEnvironment.STG and compatibility == DomainCompatibilityMode.NONE:
            violations.append(
                DomainPolicyViolation(
                    subject=subject,
                    rule="STG_COMPAT_RECOMMENDATION",
                    message="스테이징(STG) 환경에서는 최소 BACKWARD 이상의 호환성 모드를 권장합니다.",
                    severity="warning",
                )
            )

        return violations
