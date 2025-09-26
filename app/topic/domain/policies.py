"""Topic 정책 검증 로직 - 네이밍 규칙 및 환경별 가드레일"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass

from .models import Environment, PolicyViolation, TopicSpec


class PolicyRule(ABC):
    """정책 규칙 인터페이스"""

    @abstractmethod
    def validate(self, spec: TopicSpec) -> list[PolicyViolation]:
        """토픽 명세 검증"""
        ...


@dataclass(slots=True, frozen=True)
class NamingPolicy:
    """네이밍 정책"""

    pattern: str = r"^((dev|stg|prod)\.)[a-z0-9._-]+$"
    forbidden_prefixes: tuple[str, ...] = ("tmp.", "test.")
    reserved_words: tuple[str, ...] = (
        "__consumer_offsets",
        "__transaction_state",
        "_schemas",
        "connect-configs",
        "connect-offsets",
        "connect-status",
    )

    def validate(self, spec: TopicSpec) -> list[PolicyViolation]:
        """네이밍 규칙 검증"""
        violations = []

        # 정규식 패턴 검증
        if not re.match(self.pattern, spec.name):
            violations.append(
                PolicyViolation(
                    name=spec.name,
                    rule="naming.pattern",
                    message=f"Topic name '{spec.name}' does not match pattern '{self.pattern}'",
                    field="name",
                )
            )

        # 금지된 접두사 검증 - 리스트 컴프리헨션으로 최적화
        forbidden_violations = [
            PolicyViolation(
                name=spec.name,
                rule="naming.forbidden_prefix",
                message=f"Prefix '{prefix}' is forbidden in {spec.environment.value} environment",
                severity="error" if spec.environment == Environment.PROD else "warning",
                field="name",
            )
            for prefix in self.forbidden_prefixes
            if spec.name.startswith(prefix)
        ]
        violations.extend(forbidden_violations)

        # 예약어 검증
        topic_base_name = spec.name.split(".", 1)[1] if "." in spec.name else spec.name
        if topic_base_name in self.reserved_words:
            violations.append(
                PolicyViolation(
                    name=spec.name,
                    rule="naming.reserved_word",
                    message=f"Topic name '{topic_base_name}' is a reserved word",
                    severity="error",
                    field="name",
                )
            )

        return violations


@dataclass(slots=True, frozen=True)
class EnvironmentGuardrails:
    """환경별 가드레일 정책"""

    def validate(self, spec: TopicSpec) -> list[PolicyViolation]:
        """환경별 가드레일 검증"""
        if not spec.config:
            return []

        violations = []
        env = spec.environment

        if env == Environment.PROD:
            violations.extend(self._validate_prod_guardrails(spec))
        elif env == Environment.STG:
            violations.extend(self._validate_stg_guardrails(spec))
        elif env == Environment.DEV:
            violations.extend(self._validate_dev_guardrails(spec))

        return violations

    def _validate_prod_guardrails(self, spec: TopicSpec) -> list[PolicyViolation]:
        """프로덕션 환경 가드레일"""
        config = spec.config
        if not config:
            return []

        violations = []
        
        # 복제 팩터 최소 3
        if config.replication_factor < 3:
            violations.append(
                PolicyViolation(
                    name=spec.name,
                    rule="prod.min_replication_factor",
                    message=f"Replication factor must be >= 3 in prod (current: {config.replication_factor})",
                    field="config.replication_factor",
                )
            )

        # min.insync.replicas 최소 2
        if config.min_insync_replicas is None or config.min_insync_replicas < 2:
            violations.append(
                PolicyViolation(
                    name=spec.name,
                    rule="prod.min_insync_replicas",
                    message=f"min.insync.replicas must be >= 2 in prod (current: {config.min_insync_replicas})",
                    field="config.min_insync_replicas",
                )
            )

        # 보존 기간 최소 7일
        min_retention_ms = 7 * 24 * 60 * 60 * 1000  # 7일
        if config.retention_ms is not None and config.retention_ms < min_retention_ms:
            violations.append(
                PolicyViolation(
                    name=spec.name,
                    rule="prod.min_retention",
                    message=f"Retention must be >= 7 days in prod (current: {config.retention_ms}ms)",
                    field="config.retention_ms",
                )
            )

        # 파티션 수 제한 (1-100)
        if config.partitions > 100:
            violations.append(
                PolicyViolation(
                    name=spec.name,
                    rule="prod.max_partitions",
                    message=f"Partitions must be <= 100 in prod (current: {config.partitions})",
                    field="config.partitions",
                )
            )

        return violations

    def _validate_stg_guardrails(self, spec: TopicSpec) -> list[PolicyViolation]:
        """스테이징 환경 가드레일"""
        violations = []
        config = spec.config

        if not config:
            return violations

        # 복제 팩터 최소 2
        if config.replication_factor < 2:
            violations.append(
                PolicyViolation(
                    name=spec.name,
                    rule="stg.min_replication_factor",
                    message=f"Replication factor must be >= 2 in stg (current: {config.replication_factor})",
                    severity="warning",
                    field="config.replication_factor",
                )
            )

        # 파티션 수 제한 (1-50)
        if config.partitions > 50:
            violations.append(
                PolicyViolation(
                    name=spec.name,
                    rule="stg.max_partitions",
                    message=f"Partitions should be <= 50 in stg (current: {config.partitions})",
                    severity="warning",
                    field="config.partitions",
                )
            )

        return violations

    def _validate_dev_guardrails(self, spec: TopicSpec) -> list[PolicyViolation]:
        """개발 환경 가드레일"""
        violations = []
        config = spec.config

        if not config:
            return violations

        # 보존 기간 최대 3일
        max_retention_ms = 3 * 24 * 60 * 60 * 1000  # 3일
        if config.retention_ms is not None and config.retention_ms > max_retention_ms:
            violations.append(
                PolicyViolation(
                    name=spec.name,
                    rule="dev.max_retention",
                    message=f"Retention should be <= 3 days in dev (current: {config.retention_ms}ms)",
                    severity="warning",
                    field="config.retention_ms",
                )
            )

        # 파티션 수 제한 (1-10)
        if config.partitions > 10:
            violations.append(
                PolicyViolation(
                    name=spec.name,
                    rule="dev.max_partitions",
                    message=f"Partitions should be <= 10 in dev (current: {config.partitions})",
                    severity="warning",
                    field="config.partitions",
                )
            )

        return violations


@dataclass(slots=True, frozen=True)
class CompressionPolicy:
    """압축 정책"""

    def validate(self, spec: TopicSpec) -> list[PolicyViolation]:
        """압축 설정 검증"""
        if not spec.config:
            return []

        violations = []

        # 프로덕션에서는 압축 권장
        if spec.environment == Environment.PROD and spec.config.compression_type.value == "none":
            violations.append(
                PolicyViolation(
                    name=spec.name,
                    rule="compression.recommended",
                    message="Compression is recommended in prod environment",
                    severity="warning",
                    field="config.compression_type",
                )
            )

        return violations


class TopicPolicyEngine:
    """토픽 정책 엔진"""

    def __init__(
        self,
        naming_policy: NamingPolicy | None = None,
        guardrails_policy: EnvironmentGuardrails | None = None,
        compression_policy: CompressionPolicy | None = None,
    ) -> None:
        self.naming_policy = naming_policy or NamingPolicy()
        self.guardrails_policy = guardrails_policy or EnvironmentGuardrails()
        self.compression_policy = compression_policy or CompressionPolicy()

    def validate_spec(self, spec: TopicSpec) -> list[PolicyViolation]:
        """토픽 명세 검증"""
        violations = []

        # 네이밍 정책 검증
        violations.extend(self.naming_policy.validate(spec))

        # 환경별 가드레일 검증
        violations.extend(self.guardrails_policy.validate(spec))

        # 압축 정책 검증
        violations.extend(self.compression_policy.validate(spec))

        return violations

    def validate_batch(self, specs: list[TopicSpec]) -> list[PolicyViolation]:
        """배치 검증 - 리스트 컴프리헨션으로 최적화"""
        return [
            violation
            for spec in specs
            for violation in self.validate_spec(spec)
        ]


# 기본 정책 엔진 인스턴스
default_policy_engine = TopicPolicyEngine()
