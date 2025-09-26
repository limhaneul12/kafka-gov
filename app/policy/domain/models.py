"""Policy 도메인 모델"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum
from typing import Any, TypeAlias


class Environment(Enum):
    """환경 구분"""
    
    DEV = "dev"
    STG = "stg"
    PROD = "prod"


class ResourceType(Enum):
    """리소스 타입"""
    
    TOPIC = "topic"
    SCHEMA = "schema"


class PolicySeverity(Enum):
    """정책 위반 심각도"""
    
    WARNING = "warning"  # 경고 (허용)
    ERROR = "error"      # 오류 (차단)
    CRITICAL = "critical" # 치명적 (즉시 차단)


@dataclass(slots=True, frozen=True)
class PolicyViolation:
    """정책 위반 정보"""
    
    resource_type: ResourceType
    resource_name: str
    rule_id: str
    message: str
    severity: PolicySeverity
    field: str | None = None
    current_value: Any = None
    expected_value: Any = None


@dataclass(slots=True, frozen=True)
class PolicyContext:
    """정책 평가 컨텍스트"""
    
    environment: Environment
    resource_type: ResourceType
    actor: str  # 요청자
    metadata: dict[str, Any] | None = None


PolicyTarget: TypeAlias = dict[str, Any]  # 정책 대상 (Topic/Schema spec)


class PolicyRule(ABC):
    """정책 규칙 인터페이스"""
    
    @property
    @abstractmethod
    def rule_id(self) -> str:
        """규칙 식별자"""
        ...
    
    @property
    @abstractmethod
    def description(self) -> str:
        """규칙 설명"""
        ...
    
    @abstractmethod
    def validate(
        self, 
        target: PolicyTarget, 
        context: PolicyContext
    ) -> list[PolicyViolation]:
        """정책 검증
        
        Args:
            target: 검증 대상 (Topic/Schema spec)
            context: 평가 컨텍스트
            
        Returns:
            정책 위반 목록
        """
        ...


@dataclass(slots=True, frozen=True)
class NamingRule(PolicyRule):
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
        self, 
        target: PolicyTarget, 
        context: PolicyContext
    ) -> list[PolicyViolation]:
        violations: list[PolicyViolation] = []
        name = self._extract_name(target, context.resource_type)
        
        if not re.match(self.pattern, name):
            violations.append(
                PolicyViolation(
                    resource_type=context.resource_type,
                    resource_name=name,
                    rule_id=self.rule_id,
                    message=f"Name '{name}' does not match pattern '{self.pattern}'",
                    severity=PolicySeverity.ERROR,
                    field="name",
                    current_value=name,
                    expected_value=self.pattern,
                )
            )
        
        # 환경별 금지 접두사 검사
        if context.environment == Environment.PROD:
            for prefix in self.forbidden_prefixes:
                if name.startswith(prefix):
                    violations.append(
                        PolicyViolation(
                            resource_type=context.resource_type,
                            resource_name=name,
                            rule_id="naming.forbidden_prefix",
                            message=f"Prefix '{prefix}' is forbidden in {context.environment.value}",
                            severity=PolicySeverity.ERROR,
                            field="name",
                            current_value=name,
                        )
                    )
        return violations
    
    def _extract_name(self, target: PolicyTarget, resource_type: ResourceType) -> str:
        """타겟에서 이름 추출"""
        if resource_type == ResourceType.TOPIC:
            return target.get("name", "")
        elif resource_type == ResourceType.SCHEMA:
            return target.get("subject", "")
        return ""


@dataclass(slots=True, frozen=True)
class ConfigurationRule(PolicyRule):
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
        self, 
        target: PolicyTarget, 
        context: PolicyContext
    ) -> list[PolicyViolation]:
        violations: list[PolicyViolation] = []
        config = target.get("config", {})
        value = config.get(self.config_key)
        name = self._extract_name(target, context.resource_type)
        
        # 필수값 검사
        if self.required and value is None:
            violations.append(
                PolicyViolation(
                    resource_type=context.resource_type,
                    resource_name=name,
                    rule_id=self.rule_id,
                    message=f"Required config '{self.config_key}' is missing",
                    severity=PolicySeverity.ERROR,
                    field=f"config.{self.config_key}",
                )
            )
            return violations
        
        if value is None:
            return violations
        
        # 범위 검사
        if self.min_value is not None and value < self.min_value:
            violations.append(
                PolicyViolation(
                    resource_type=context.resource_type,
                    resource_name=name,
                    rule_id=self.rule_id,
                    message=f"Config '{self.config_key}' value {value} is below minimum {self.min_value}",
                    severity=PolicySeverity.ERROR,
                    field=f"config.{self.config_key}",
                    current_value=value,
                    expected_value=f">= {self.min_value}",
                )
            )
        
        if self.max_value is not None and value > self.max_value:
            violations.append(
                PolicyViolation(
                    resource_type=context.resource_type,
                    resource_name=name,
                    rule_id=self.rule_id,
                    message=f"Config '{self.config_key}' value {value} exceeds maximum {self.max_value}",
                    severity=PolicySeverity.ERROR,
                    field=f"config.{self.config_key}",
                    current_value=value,
                    expected_value=f"<= {self.max_value}",
                )
            )
        
        # 허용값 검사
        if self.allowed_values and value not in self.allowed_values:
            violations.append(
                PolicyViolation(
                    resource_type=context.resource_type,
                    resource_name=name,
                    rule_id=self.rule_id,
                    message=f"Config '{self.config_key}' value '{value}' is not allowed. Allowed: {list(self.allowed_values)}",
                    severity=PolicySeverity.ERROR,
                    field=f"config.{self.config_key}",
                    current_value=value,
                    expected_value=list(self.allowed_values),
                )
            )
        
        return violations
    
    def _extract_name(self, target: PolicyTarget, resource_type: ResourceType) -> str:
        """타겟에서 이름 추출"""
        if resource_type == ResourceType.TOPIC:
            return target.get("name", "")
        elif resource_type == ResourceType.SCHEMA:
            return target.get("subject", "")
        return ""


@dataclass(slots=True, frozen=True)
class PolicySet:
    """환경별 정책 집합"""
    
    environment: Environment
    resource_type: ResourceType
    rules: tuple[PolicyRule, ...]
    
    def validate_batch(
        self, 
        targets: Iterable[PolicyTarget], 
        actor: str,
        metadata: dict[str, Any] | None = None
    ) -> list[PolicyViolation]:
        """배치 검증"""
        context = PolicyContext(
            environment=self.environment,
            resource_type=self.resource_type,
            actor=actor,
            metadata=metadata,
        )
        
        violations: list[PolicyViolation] = []
        for target in targets:
            for rule in self.rules:
                violations.extend(rule.validate(target, context))
        
        return violations


class PolicyEngine:
    """통합 정책 엔진"""
    
    def __init__(self) -> None:
        self._policy_sets: dict[tuple[Environment, ResourceType], PolicySet] = {}
    
    def register_policy_set(self, policy_set: PolicySet) -> None:
        """정책 집합 등록"""
        key = (policy_set.environment, policy_set.resource_type)
        self._policy_sets[key] = policy_set
    
    def evaluate(
        self,
        environment: Environment,
        resource_type: ResourceType,
        targets: Iterable[PolicyTarget],
        actor: str,
        metadata: dict[str, Any] | None = None,
    ) -> list[PolicyViolation]:
        """정책 평가"""
        key = (environment, resource_type)
        policy_set = self._policy_sets.get(key)
        
        if not policy_set:
            return []  # 정책이 없으면 통과
        
        return policy_set.validate_batch(targets, actor, metadata)
    
    def get_policy_set(
        self, 
        environment: Environment, 
        resource_type: ResourceType
    ) -> PolicySet | None:
        """정책 집합 조회"""
        key = (environment, resource_type)
        return self._policy_sets.get(key)
    
    def list_environments(self) -> list[Environment]:
        """등록된 환경 목록"""
        return list({env for env, _ in self._policy_sets})
    
    def list_resource_types(self, environment: Environment) -> list[ResourceType]:
        """환경별 리소스 타입 목록"""
        return [rt for env, rt in self._policy_sets if env == environment]
