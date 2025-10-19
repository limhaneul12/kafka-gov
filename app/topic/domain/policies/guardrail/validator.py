"""Guardrail Policy Validator

Validates topic configurations against guardrail presets.
"""

from dataclasses import dataclass
from typing import Annotated

from typing_extensions import Doc

from .....shared.domain.policy_types import (
    DomainPolicySeverity,
    DomainPolicyViolation,
    DomainResourceType,
)
from ...models import DomainTopicConfig
from .preset.preset_schema import BaseGuardrailPreset


@dataclass(frozen=True)
class ValidationRule:
    """Declarative validation rule"""

    rule_id: str
    config_field: str  # Field name in DomainTopicConfig
    preset_field: str  # Field name in BaseGuardrailPreset
    severity: DomainPolicySeverity
    required: bool = True  # False = optional (warning if missing)

    def validate(
        self, config: DomainTopicConfig, preset: BaseGuardrailPreset, topic_name: str
    ) -> DomainPolicyViolation | None:
        """Execute validation rule

        Args:
            config: Topic configuration
            preset: Guardrail preset
            topic_name: Topic name (for error messages)

        Returns:
            Violation if validation fails, None otherwise
        """
        config_value = getattr(config, self.config_field)
        preset_value = getattr(preset, self.preset_field)

        # Skip if preset doesn't define this rule
        if preset_value is None:
            return None

        # Check if value is missing
        if config_value is None:
            if not self.required:
                return DomainPolicyViolation(
                    resource_type=DomainResourceType.TOPIC,
                    resource_name=topic_name,
                    rule_id=self.rule_id,
                    message=f"Topic '{topic_name}': {self.rule_id} not set (recommended: {preset_value})",
                    severity=DomainPolicySeverity.WARNING,
                )
            return None

        # Check if value is too low
        if config_value < preset_value:
            return DomainPolicyViolation(
                resource_type=DomainResourceType.TOPIC,
                resource_name=topic_name,
                rule_id=self.rule_id,
                message=(
                    f"Topic '{topic_name}': {self.rule_id} too low "
                    f"(min: {preset_value}, got: {config_value})"
                ),
                severity=self.severity,
            )

        return None


# ============================================================================
# Validation Rules Configuration
# ============================================================================

VALIDATION_RULES: list[ValidationRule] = [
    ValidationRule(
        rule_id="replication_factor",
        config_field="replication_factor",
        preset_field="replication_factor",
        severity=DomainPolicySeverity.ERROR,
    ),
    ValidationRule(
        rule_id="min_insync_replicas",
        config_field="min_insync_replicas",
        preset_field="min_insync_replicas",
        severity=DomainPolicySeverity.ERROR,
        required=False,  # Optional field
    ),
    ValidationRule(
        rule_id="partitions",
        config_field="partitions",
        preset_field="partitions",
        severity=DomainPolicySeverity.WARNING,  # Warning, not error
    ),
    ValidationRule(
        rule_id="retention_ms",
        config_field="retention_ms",
        preset_field="retention_ms",
        severity=DomainPolicySeverity.WARNING,
        required=False,
    ),
]


class GuardrailValidator:
    """Validates topic configurations against guardrail presets"""

    def __init__(self, preset: BaseGuardrailPreset) -> None:
        """Initialize validator with guardrail preset

        Args:
            preset: Guardrail preset to apply (Dev/Stg/Prod/Custom)
        """
        self.preset = preset

    def validate(
        self,
        config: DomainTopicConfig,
        topic_name: Annotated[str, Doc("Topic name for error messages")],
    ) -> list[DomainPolicyViolation]:
        """Validate single topic configuration

        Args:
            config: Topic configuration to validate
            topic_name: Topic name (for error messages)

        Returns:
            List of violations (empty if valid)
        """
        violations: list[DomainPolicyViolation] = []

        # Apply all validation rules
        for rule in VALIDATION_RULES:
            violation = rule.validate(config, self.preset, topic_name)
            if violation:
                violations.append(violation)

        return violations

    def validate_batch(
        self, configs: list[tuple[str, DomainTopicConfig]]
    ) -> list[DomainPolicyViolation]:
        """Validate multiple topic configurations

        Args:
            configs: List of (topic_name, config) tuples to validate

        Returns:
            List of all violations across all topics
        """
        all_violations: list[DomainPolicyViolation] = []

        for topic_name, config in configs:
            violations = self.validate(config, topic_name)
            all_violations.extend(violations)

        return all_violations
