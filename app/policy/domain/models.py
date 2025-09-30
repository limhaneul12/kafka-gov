"""Policy 도메인 모델"""

from __future__ import annotations

import re
from collections.abc import Iterable
from enum import Enum
from typing import Any, Protocol, TypeAlias

import msgspec


class DomainEnvironment(Enum):
    """환경 구분"""

    DEV = "dev"
    STG = "stg"
    PROD = "prod"


class DomainResourceType(Enum):
    """리소스 타입"""

    TOPIC = "topic"
    SCHEMA = "schema"


class DomainPolicySeverity(Enum):
    """정책 위반 심각도"""

    WARNING = "warning"  # 경고 (허용)
    ERROR = "error"  # 오류 (차단)
    CRITICAL = "critical"  # 치명적 (즉시 차단)


PolicyTarget: TypeAlias = dict[str, Any]  # 정책 대상 (Topic/Schema spec)


class PolicyRule(Protocol):
    """정책 규칙 프로토콜"""

    @property
    def rule_id(self) -> str:
        """규칙 식별자"""
        ...

    @property
    def description(self) -> str:
        """규칙 설명"""
        ...

    def validate(
        self, target: PolicyTarget, context: DomainPolicyContext
    ) -> list[DomainPolicyViolation]:
        """정책 검증

        Args:
            target: 검증 대상 (Topic/Schema spec)
            context: 평가 컨텍스트

        Returns:
            정책 위반 목록
        """
        ...


class DomainPolicyViolation(msgspec.Struct, frozen=True):
    """정책 위반 정보"""

    resource_type: DomainResourceType
    resource_name: str
    rule_id: str
    message: str
    severity: DomainPolicySeverity
    field: str | None = None
    current_value: Any = None
    expected_value: Any = None


class DomainPolicyContext(msgspec.Struct, frozen=True):
    """정책 평가 컨텍스트"""

    environment: DomainEnvironment
    resource_type: DomainResourceType
    actor: str
    metadata: dict[str, Any] | None = None


class DomainNamingRule(msgspec.Struct):
    """네이밍 규칙"""

    pattern: str
    forbidden_prefixes: tuple[str, ...] = ()
    forbidden_suffixes: tuple[str, ...] = ()

    @property
    def rule_id(self) -> str:
        return "naming.pattern"

    @property
    def description(self) -> str:
        return f"Name must match pattern: {self.pattern}"

    def validate(
        self, target: PolicyTarget, context: DomainPolicyContext
    ) -> list[DomainPolicyViolation]:
        violations: list[DomainPolicyViolation] = []
        name = self._extract_name(target, context.resource_type)

        if not re.match(self.pattern, name):
            violations.append(
                DomainPolicyViolation(
                    resource_type=context.resource_type,
                    resource_name=name,
                    rule_id=self.rule_id,
                    message=f"Name '{name}' does not match pattern '{self.pattern}'",
                    severity=DomainPolicySeverity.ERROR,
                    field="name",
                    current_value=name,
                    expected_value=self.pattern,
                )
            )

        # 환경별 금지 접두사 검사
        if context.environment == DomainEnvironment.PROD:
            violations.extend(
                [
                    DomainPolicyViolation(
                        resource_type=context.resource_type,
                        resource_name=name,
                        rule_id="naming.forbidden_prefix",
                        message=f"Prefix '{prefix}' is forbidden in {context.environment.value}",
                        severity=DomainPolicySeverity.ERROR,
                        field="name",
                        current_value=name,
                    )
                    for prefix in self.forbidden_prefixes
                    if name.startswith(prefix)
                ]
            )
        return violations

    def _extract_name(self, target: PolicyTarget, resource_type: DomainResourceType) -> str:
        """타겟에서 이름 추출"""
        if resource_type == DomainResourceType.TOPIC:
            return target.get("name", "")
        elif resource_type == DomainResourceType.SCHEMA:
            return target.get("subject", "")
        else:
            raise ValueError(f"unsupported resource type: {resource_type}")


class DomainConfigurationRule(msgspec.Struct):
    """설정값 규칙"""

    config_key: str
    min_value: int | float | None = None
    max_value: int | float | None = None
    allowed_values: tuple[Any, ...] | None = None
    required: bool = False

    @property
    def rule_id(self) -> str:
        return f"config.{self.config_key}"

    @property
    def description(self) -> str:
        constraints = []
        if self.required:
            constraints.append("required")
        if self.min_value is not None:
            constraints.append(f"min={self.min_value}")
        if self.max_value is not None:
            constraints.append(f"max={self.max_value}")
        if self.allowed_values:
            constraints.append(f"allowed={list(self.allowed_values)}")

        constraint_str = ", ".join(constraints) if constraints else "no constraints"
        return f"Config '{self.config_key}': {constraint_str}"

    def validate(
        self, target: PolicyTarget, context: DomainPolicyContext
    ) -> list[DomainPolicyViolation]:
        violations: list[DomainPolicyViolation] = []
        config = target.get("config", {})
        value = config.get(self.config_key)
        name = self._extract_name(target, context.resource_type)

        # 필수값 검사
        if self.required and value is None:
            violations.append(
                DomainPolicyViolation(
                    resource_type=context.resource_type,
                    resource_name=name,
                    rule_id=self.rule_id,
                    message=f"Required config '{self.config_key}' is missing",
                    severity=DomainPolicySeverity.ERROR,
                    field=f"config.{self.config_key}",
                )
            )
            return violations

        if value is None:
            return violations

        # 범위 검사
        if self.min_value is not None and value < self.min_value:
            violations.append(
                DomainPolicyViolation(
                    resource_type=context.resource_type,
                    resource_name=name,
                    rule_id=self.rule_id,
                    message=f"Config '{self.config_key}' value {value} is below minimum {self.min_value}",
                    severity=DomainPolicySeverity.ERROR,
                    field=f"config.{self.config_key}",
                    current_value=value,
                    expected_value=f">= {self.min_value}",
                )
            )

        if self.max_value is not None and value > self.max_value:
            violations.append(
                DomainPolicyViolation(
                    resource_type=context.resource_type,
                    resource_name=name,
                    rule_id=self.rule_id,
                    message=f"Config '{self.config_key}' value {value} exceeds maximum {self.max_value}",
                    severity=DomainPolicySeverity.ERROR,
                    field=f"config.{self.config_key}",
                    current_value=value,
                    expected_value=f"<= {self.max_value}",
                )
            )

        # 허용값 검사
        if self.allowed_values and value not in self.allowed_values:
            violations.append(
                DomainPolicyViolation(
                    resource_type=context.resource_type,
                    resource_name=name,
                    rule_id=self.rule_id,
                    message=f"Config '{self.config_key}' value '{value}' is not allowed. Allowed: {list(self.allowed_values)}",
                    severity=DomainPolicySeverity.ERROR,
                    field=f"config.{self.config_key}",
                    current_value=value,
                    expected_value=list(self.allowed_values),
                )
            )

        return violations

    def _extract_name(self, target: PolicyTarget, resource_type: DomainResourceType) -> str:
        """타겟에서 이름 추출"""
        if resource_type == DomainResourceType.TOPIC:
            return target.get("name", "")
        elif resource_type == DomainResourceType.SCHEMA:
            return target.get("subject", "")
        else:
            raise ValueError(f"unsupported resource type: {resource_type}")


class DomainPolicySet(msgspec.Struct):
    """환경별 정책 집합"""

    environment: DomainEnvironment
    resource_type: DomainResourceType
    rules: tuple[PolicyRule, ...]

    def __post_init__(self) -> None:
        if not self.rules:
            raise ValueError("at least one rule is required")

    def validate_batch(
        self, targets: Iterable[PolicyTarget], actor: str, metadata: dict[str, Any] | None = None
    ) -> list[DomainPolicyViolation]:
        """배치 검증"""
        context = DomainPolicyContext(
            environment=self.environment,
            resource_type=self.resource_type,
            actor=actor,
            metadata=metadata,
        )

        violations: list[DomainPolicyViolation] = []
        for target in targets:
            for rule in self.rules:
                violations.extend(rule.validate(target, context))

        return violations


class PolicyEngine:
    """통합 정책 엔진"""

    def __init__(self) -> None:
        self._policy_sets: dict[tuple[DomainEnvironment, DomainResourceType], DomainPolicySet] = {}

    def register_policy_set(self, policy_set: DomainPolicySet) -> None:
        """정책 집합 등록"""
        key = (policy_set.environment, policy_set.resource_type)
        self._policy_sets[key] = policy_set

    def evaluate(
        self,
        environment: DomainEnvironment,
        resource_type: DomainResourceType,
        targets: Iterable[PolicyTarget],
        actor: str,
        metadata: dict[str, Any] | None = None,
    ) -> list[DomainPolicyViolation]:
        """정책 평가"""
        key = (environment, resource_type)
        policy_set = self._policy_sets.get(key)

        if not policy_set:
            return []  # 정책이 없으면 통과

        return policy_set.validate_batch(targets, actor, metadata)

    def get_policy_set(
        self, environment: DomainEnvironment, resource_type: DomainResourceType
    ) -> DomainPolicySet | None:
        """정책 집합 조회"""
        key = (environment, resource_type)
        return self._policy_sets.get(key)

    def list_environments(self) -> list[DomainEnvironment]:
        """등록된 환경 목록"""
        return list({env for env, _ in self._policy_sets})

    def list_resource_types(self, environment: DomainEnvironment) -> list[DomainResourceType]:
        """환경별 리소스 타입 목록"""
        return [rt for env, rt in self._policy_sets if env == environment]
