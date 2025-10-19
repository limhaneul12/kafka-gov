"""Topic Policy Orchestrator - Coordinates all policy validations

Supports 3 validation modes:
1. Naming only
2. Guardrail only
3. Both (naming + guardrail)
"""

from typing import Annotated

from typing_extensions import Doc

from .....shared.domain.policy_types import DomainPolicyViolation
from ...models import DomainTopicSpec
from ..guardrail.preset.preset_schema import BaseGuardrailPreset
from ..guardrail.validator import GuardrailValidator
from ..naming.rule.rule_schema import BaseNamingRules
from ..naming.validator import NamingValidator


class TopicPolicyValidator:
    """Orchestrates naming and guardrail validations

    Supports flexible validation modes:
    - Naming only: Pass naming_rules, leave guardrail_preset as None
    - Guardrail only: Pass guardrail_preset, leave naming_rules as None
    - Both: Pass both parameters
    """

    def __init__(
        self,
        naming_rules: Annotated[
            BaseNamingRules | None, Doc("Naming rules (None = skip naming validation)")
        ] = None,
        guardrail_preset: Annotated[
            BaseGuardrailPreset | None, Doc("Guardrail preset (None = skip guardrail validation)")
        ] = None,
    ) -> None:
        """Initialize policy validator

        Args:
            naming_rules: Naming rules to apply (None = skip naming validation)
            guardrail_preset: Guardrail preset to apply (None = skip guardrail validation)

        Raises:
            ValueError: If both parameters are None
        """
        if naming_rules is None and guardrail_preset is None:
            raise ValueError("At least one policy (naming or guardrail) must be provided")

        self.naming_validator = NamingValidator(naming_rules) if naming_rules else None
        self.guardrail_validator = (
            GuardrailValidator(guardrail_preset) if guardrail_preset else None
        )

    def validate(self, spec: DomainTopicSpec) -> list[DomainPolicyViolation]:
        """Validate single topic spec

        Args:
            spec: Topic specification to validate

        Returns:
            List of violations (empty if valid)
        """
        violations: list[DomainPolicyViolation] = []

        # 1. Naming validation
        if self.naming_validator:
            naming_violations = self.naming_validator.validate(spec.name)
            violations.extend(naming_violations)

        # 2. Guardrail validation (only for non-delete actions)
        if self.guardrail_validator and spec.config:
            guardrail_violations = self.guardrail_validator.validate(spec.config, spec.name)
            violations.extend(guardrail_violations)

        return violations

    def validate_batch(self, specs: list[DomainTopicSpec]) -> list[DomainPolicyViolation]:
        """Validate multiple topic specs

        Args:
            specs: List of topic specifications to validate

        Returns:
            List of all violations across all topics
        """
        all_violations: list[DomainPolicyViolation] = []

        # Collect all names and configs
        topic_names: list[str] = [spec.name for spec in specs]
        topic_configs = [(spec.name, spec.config) for spec in specs if spec.config]

        # 1. Batch naming validation
        if self.naming_validator:
            naming_violations = self.naming_validator.validate_batch(topic_names)
            all_violations.extend(naming_violations)

        # 2. Batch guardrail validation
        if self.guardrail_validator and topic_configs:
            guardrail_violations = self.guardrail_validator.validate_batch(topic_configs)
            all_violations.extend(guardrail_violations)

        return all_violations


# ============================================================================
# Convenience Factory Functions
# ============================================================================


def create_naming_only_validator(rules: BaseNamingRules) -> TopicPolicyValidator:
    """Create validator with naming rules only

    Args:
        rules: Naming rules to apply

    Returns:
        TopicPolicyValidator configured for naming validation only

    Example:
        >>> from ..naming import StrictNamingRules
        >>> validator = create_naming_only_validator(StrictNamingRules())
        >>> violations = validator.validate(spec)
    """
    return TopicPolicyValidator(naming_rules=rules, guardrail_preset=None)


def create_guardrail_only_validator(preset: BaseGuardrailPreset) -> TopicPolicyValidator:
    """Create validator with guardrail preset only

    Args:
        preset: Guardrail preset to apply

    Returns:
        TopicPolicyValidator configured for guardrail validation only

    Example:
        >>> from ..guardrail import ProdGuardrailPreset
        >>> validator = create_guardrail_only_validator(ProdGuardrailPreset())
        >>> violations = validator.validate(spec)
    """
    return TopicPolicyValidator(naming_rules=None, guardrail_preset=preset)


def create_full_validator(
    rules: BaseNamingRules, preset: BaseGuardrailPreset
) -> TopicPolicyValidator:
    """Create validator with both naming and guardrail policies

    Args:
        rules: Naming rules to apply
        preset: Guardrail preset to apply

    Returns:
        TopicPolicyValidator configured for full validation

    Example:
        >>> from ..naming import StrictNamingRules
        >>> from ..guardrail import ProdGuardrailPreset
        >>> validator = create_full_validator(
        ...     StrictNamingRules(),
        ...     ProdGuardrailPreset()
        ... )
        >>> violations = validator.validate(spec)
    """
    return TopicPolicyValidator(naming_rules=rules, guardrail_preset=preset)
