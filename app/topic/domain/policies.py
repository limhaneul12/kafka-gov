"""Topic 정책 검증 로직 - 깔끔하게 리팩토링된 버전"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol

import msgspec

from ...shared.domain.policy_types import DomainPolicySeverity, DomainResourceType
from .models import DomainEnvironment, DomainPolicyViolation, DomainTopicSpec


class PolicyRule(Protocol):
    """정책 규칙 프로토콜"""

    def validate(self, spec: DomainTopicSpec) -> list[DomainPolicyViolation]:
        """토픽 명세 검증"""
        ...


# ============================================================================
# 검증 규칙 설정 (데이터 중심)
# ============================================================================


@dataclass(frozen=True)
class GuardrailRule:
    """가드레일 규칙 정의"""

    rule_id: str
    field: str
    message_template: str
    severity: DomainPolicySeverity


class GuardrailConfig(msgspec.Struct, frozen=True):
    """환경별 가드레일 설정"""

    # 복제 팩터
    min_replication_factor: int | None = None

    # min.insync.replicas
    min_insync_replicas: int | None = None

    # 보존 기간 (밀리초)
    min_retention_ms: int | None = None
    max_retention_ms: int | None = None

    # 파티션 수
    max_partitions: int | None = None


# 환경별 가드레일 설정 (선언적)
GUARDRAIL_CONFIGS: dict[DomainEnvironment, GuardrailConfig] = {
    DomainEnvironment.PROD: GuardrailConfig(
        min_replication_factor=3,
        min_insync_replicas=2,
        min_retention_ms=7 * 24 * 60 * 60 * 1000,  # 7일
        max_partitions=100,
    ),
    DomainEnvironment.STG: GuardrailConfig(
        min_replication_factor=2,
        max_partitions=50,
    ),
    DomainEnvironment.DEV: GuardrailConfig(
        max_retention_ms=3 * 24 * 60 * 60 * 1000,  # 3일
        max_partitions=10,
    ),
}


# ============================================================================
# 정책 클래스들
# ============================================================================


class NamingPolicy(msgspec.Struct):
    """네이밍 정책"""

    # 토픽 이름: 소문자, 숫자, 점(.), 밑줄(_), 하이픈(-) 허용
    pattern: str = r"^[a-z0-9._-]+$"
    forbidden_prefixes: tuple[str, ...] = ("tmp.", "test.")
    reserved_words: tuple[str, ...] = (
        "__consumer_offsets",
        "__transaction_state",
        "_schemas",
        "connect-configs",
        "connect-offsets",
        "connect-status",
    )

    def validate(self, spec: DomainTopicSpec) -> list[DomainPolicyViolation]:
        """네이밍 규칙 검증"""
        violations = []

        # 1. 정규식 패턴 검증
        if not re.match(self.pattern, spec.name):
            violations.append(
                self._create_violation(
                    spec.name,
                    "naming.pattern",
                    f"Topic name '{spec.name}' does not match pattern '{self.pattern}'",
                    DomainPolicySeverity.ERROR,
                    "name",
                )
            )

        # 2. 금지된 접두사 검증
        violations.extend(
            [
                self._create_violation(
                    spec.name,
                    "naming.forbidden_prefix",
                    f"Prefix '{prefix}' is forbidden in {spec.environment.value} environment",
                    DomainPolicySeverity.ERROR
                    if spec.environment == DomainEnvironment.PROD
                    else DomainPolicySeverity.WARNING,
                    "name",
                )
                for prefix in self.forbidden_prefixes
                if spec.name.startswith(prefix)
            ]
        )

        # 3. 예약어 검증
        topic_base_name = spec.name.split(".", 1)[1] if "." in spec.name else spec.name
        if topic_base_name in self.reserved_words:
            violations.append(
                self._create_violation(
                    spec.name,
                    "naming.reserved_word",
                    f"Topic name '{topic_base_name}' is a reserved word",
                    DomainPolicySeverity.ERROR,
                    "name",
                )
            )

        return violations

    def _create_violation(
        self,
        resource_name: str,
        rule_id: str,
        message: str,
        severity: DomainPolicySeverity,
        field: str,
    ) -> DomainPolicyViolation:
        """위반 객체 생성 헬퍼"""
        return DomainPolicyViolation(
            resource_type=DomainResourceType.TOPIC,
            resource_name=resource_name,
            rule_id=rule_id,
            message=message,
            severity=severity,
            field=field,
        )


class EnvironmentGuardrails(msgspec.Struct):
    """환경별 가드레일 정책 - 선언적 설정 기반"""

    def validate(self, spec: DomainTopicSpec) -> list[DomainPolicyViolation]:
        """환경별 가드레일 검증"""
        if not spec.config:
            return []

        config_rules = GUARDRAIL_CONFIGS.get(spec.environment)
        if not config_rules:
            return []

        violations = []
        config = spec.config
        env_name = spec.environment.value

        # 복제 팩터 검증
        if (
            config_rules.min_replication_factor is not None
            and config.replication_factor < config_rules.min_replication_factor
        ):
            violations.append(
                self._create_violation(
                    spec.name,
                    f"{env_name}.min_replication_factor",
                    f"Replication factor must be >= {config_rules.min_replication_factor} in {env_name} (current: {config.replication_factor})",
                    DomainPolicySeverity.ERROR
                    if spec.environment == DomainEnvironment.PROD
                    else DomainPolicySeverity.WARNING,
                    "config.replication_factor",
                )
            )

        # min.insync.replicas 검증
        if config_rules.min_insync_replicas is not None and (
            config.min_insync_replicas is None
            or config.min_insync_replicas < config_rules.min_insync_replicas
        ):
            violations.append(
                self._create_violation(
                    spec.name,
                    f"{env_name}.min_insync_replicas",
                    f"min.insync.replicas must be >= {config_rules.min_insync_replicas} in {env_name} (current: {config.min_insync_replicas})",
                    DomainPolicySeverity.ERROR,
                    "config.min_insync_replicas",
                )
            )

        # 최소 보존 기간 검증
        if (
            config_rules.min_retention_ms is not None
            and config.retention_ms is not None
            and config.retention_ms < config_rules.min_retention_ms
        ):
            violations.append(
                self._create_violation(
                    spec.name,
                    f"{env_name}.min_retention",
                    f"Retention must be >= {config_rules.min_retention_ms // (24 * 60 * 60 * 1000)} days in {env_name} (current: {config.retention_ms}ms)",
                    DomainPolicySeverity.ERROR,
                    "config.retention_ms",
                )
            )

        # 최대 보존 기간 검증
        if (
            config_rules.max_retention_ms is not None
            and config.retention_ms is not None
            and config.retention_ms > config_rules.max_retention_ms
        ):
            violations.append(
                self._create_violation(
                    spec.name,
                    f"{env_name}.max_retention",
                    f"Retention should be <= {config_rules.max_retention_ms // (24 * 60 * 60 * 1000)} days in {env_name} (current: {config.retention_ms}ms)",
                    DomainPolicySeverity.WARNING,
                    "config.retention_ms",
                )
            )

        # 최대 파티션 수 검증
        if (
            config_rules.max_partitions is not None
            and config.partitions > config_rules.max_partitions
        ):
            violations.append(
                self._create_violation(
                    spec.name,
                    f"{env_name}.max_partitions",
                    f"Partitions {'must' if spec.environment == DomainEnvironment.PROD else 'should'} be <= {config_rules.max_partitions} in {env_name} (current: {config.partitions})",
                    DomainPolicySeverity.ERROR
                    if spec.environment == DomainEnvironment.PROD
                    else DomainPolicySeverity.WARNING,
                    "config.partitions",
                )
            )

        return violations

    def _create_violation(
        self,
        resource_name: str,
        rule_id: str,
        message: str,
        severity: DomainPolicySeverity,
        field: str,
    ) -> DomainPolicyViolation:
        """위반 객체 생성 헬퍼"""
        return DomainPolicyViolation(
            resource_type=DomainResourceType.TOPIC,
            resource_name=resource_name,
            rule_id=rule_id,
            message=message,
            severity=severity,
            field=field,
        )


class TopicPolicyEngine:
    """토픽 정책 엔진"""

    def __init__(
        self,
        naming_policy: NamingPolicy | None = None,
        guardrails_policy: EnvironmentGuardrails | None = None,
    ) -> None:
        self.naming_policy = naming_policy or NamingPolicy()
        self.guardrails_policy = guardrails_policy or EnvironmentGuardrails()

    def validate_spec(self, spec: DomainTopicSpec) -> list[DomainPolicyViolation]:
        """토픽 명세 검증"""
        return [
            *self.naming_policy.validate(spec),
            *self.guardrails_policy.validate(spec),
        ]

    def validate_batch(self, specs: list[DomainTopicSpec]) -> list[DomainPolicyViolation]:
        """배치 검증"""
        return [violation for spec in specs for violation in self.validate_spec(spec)]


# 기본 정책 엔진 인스턴스
default_policy_engine = TopicPolicyEngine()
