"""Schema 정책 검증 로직"""

import re
from collections.abc import Iterable
from dataclasses import dataclass

from .models import (
    DomainCompatibilityMode,
    DomainEnvironment,
    DomainPolicyViolation,
    DomainSchemaSpec,
)


@dataclass(slots=True, frozen=True)
class NamingPolicy:
    """스키마 subject 네이밍 정책"""

    pattern: str = r"^((dev|stg|prod)\.)[a-z0-9._-]+(-key|-value)?$"
    forbidden_prod_prefixes: tuple[str, ...] = ("tmp.", "test.")

    def validate(self, spec: DomainSchemaSpec) -> list[DomainPolicyViolation]:
        violations: list[DomainPolicyViolation] = []

        if not re.match(self.pattern, spec.subject):
            violations.append(
                DomainPolicyViolation(
                    subject=spec.subject,
                    rule="schema.naming.pattern",
                    message=f"Subject '{spec.subject}' does not match pattern '{self.pattern}'",
                    field="subject",
                )
            )

        if spec.environment == DomainEnvironment.PROD:
            prefix = spec.subject.split(".")[1] if "." in spec.subject else spec.subject
            violations.extend(
                [
                    DomainPolicyViolation(
                        subject=spec.subject,
                        rule="schema.naming.forbidden_prefix",
                        message=f"Prefix '{forbidden}' is forbidden in prod",
                        field="subject",
                    )
                    for forbidden in self.forbidden_prod_prefixes
                    if spec.subject.startswith(forbidden)
                ]
            )
            if prefix == "tmp":
                violations.append(
                    DomainPolicyViolation(
                        subject=spec.subject,
                        rule="schema.naming.forbidden_prefix",
                        message="'tmp' prefix is forbidden in prod",
                        field="subject",
                    )
                )

        return violations


@dataclass(slots=True, frozen=True)
class CompatibilityPolicy:
    """환경별 호환성 정책"""

    def validate(self, spec: DomainSchemaSpec) -> list[DomainPolicyViolation]:
        expected_modes = self._expected_modes(spec.environment)
        if spec.compatibility in expected_modes:
            return []

        expected_str = ",".join(mode.value for mode in expected_modes)
        return [
            DomainPolicyViolation(
                subject=spec.subject,
                rule="schema.compatibility.mode",
                message=(
                    f"Compatibility mode '{spec.compatibility.value}' is not allowed "
                    f"in {spec.environment.value}; expected one of [{expected_str}]"
                ),
                field="compatibility",
            )
        ]

    def _expected_modes(self, env: DomainEnvironment) -> tuple[DomainCompatibilityMode, ...]:
        if env == DomainEnvironment.PROD:
            return (DomainCompatibilityMode.FULL, DomainCompatibilityMode.FULL_TRANSITIVE)
        if env == DomainEnvironment.STG:
            return (
                DomainCompatibilityMode.BACKWARD,
                DomainCompatibilityMode.BACKWARD_TRANSITIVE,
                DomainCompatibilityMode.FULL,
                DomainCompatibilityMode.FULL_TRANSITIVE,
            )
        return (
            DomainCompatibilityMode.BACKWARD,
            DomainCompatibilityMode.BACKWARD_TRANSITIVE,
            DomainCompatibilityMode.NONE,
        )


@dataclass(slots=True, frozen=True)
class MetadataPolicy:
    """메타데이터 정책"""

    require_owner: bool = True

    def validate(self, spec: DomainSchemaSpec) -> list[DomainPolicyViolation]:
        if not self.require_owner:
            return []
        if spec.metadata is None or not spec.metadata.owner:
            return [
                DomainPolicyViolation(
                    subject=spec.subject,
                    rule="schema.metadata.owner",
                    message="Schema metadata owner is required",
                    field="metadata.owner",
                )
            ]
        return []


class SchemaPolicyEngine:
    """스키마 정책 엔진"""

    def __init__(
        self,
        naming_policy: NamingPolicy | None = None,
        compatibility_policy: CompatibilityPolicy | None = None,
        metadata_policy: MetadataPolicy | None = None,
    ) -> None:
        self.naming_policy = naming_policy or NamingPolicy()
        self.compatibility_policy = compatibility_policy or CompatibilityPolicy()
        self.metadata_policy = metadata_policy or MetadataPolicy()

    def validate_batch(self, specs: Iterable[DomainSchemaSpec]) -> list[DomainPolicyViolation]:
        violations: list[DomainPolicyViolation] = []
        for spec in specs:
            violations.extend(self.naming_policy.validate(spec))
            violations.extend(self.compatibility_policy.validate(spec))
            violations.extend(self.metadata_policy.validate(spec))
        return violations
