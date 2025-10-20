"""Policy Resolver

Resolves policy references to actual validators.
Handles 3 cases:
1. No policy → None (skip validation)
2. Preset → Built-in preset validator
3. Custom policy ID → Load from DB and create validator
"""

from ..guardrail import get_preset_spec as get_guardrail_preset_spec
from ..guardrail.preset.preset_schema import CustomGuardrailPreset
from ..management import IPolicyRepository, PolicyReference, PolicyType, StoredPolicy
from ..naming import get_strategy_spec as get_naming_strategy_spec
from ..naming.rule.rule_schema import CustomNamingRules
from .orchestrator import (
    TopicPolicyValidator,
    create_full_validator,
    create_guardrail_only_validator,
    create_naming_only_validator,
)


class PolicyResolver:
    """Resolves policy references to validators"""

    def __init__(
        self,
        naming_policy_repo: IPolicyRepository,
        guardrail_policy_repo: IPolicyRepository,
    ) -> None:
        """Initialize resolver with policy repositories

        Args:
            naming_policy_repo: Repository for naming policies
            guardrail_policy_repo: Repository for guardrail policies
        """
        self.naming_repo = naming_policy_repo
        self.guardrail_repo = guardrail_policy_repo

    async def resolve(
        self,
        naming_ref: PolicyReference | None,
        guardrail_ref: PolicyReference | None,
    ) -> TopicPolicyValidator | None:
        """Resolve policy references to validator

        Args:
            naming_ref: Naming policy reference (None = skip)
            guardrail_ref: Guardrail policy reference (None = skip)

        Returns:
            Validator if any policy is specified, None if both are None

        Raises:
            ValueError: If preset or policy_id not found

        Examples:
            # 1. No policy
            >>> await resolver.resolve(None, None)
            None

            # 2. Preset only
            >>> await resolver.resolve(
            ...     None,
            ...     PolicyReference(preset="prod")
            ... )
            TopicPolicyValidator(guardrail_only)

            # 3. Custom policy
            >>> await resolver.resolve(
            ...     PolicyReference(policy_id="uuid-123"),
            ...     PolicyReference(preset="prod")
            ... )
            TopicPolicyValidator(both)
        """
        # Case 1: No policy → None
        if not naming_ref and not guardrail_ref:
            return None

        # Resolve naming
        naming_rules = None
        if naming_ref:
            if naming_ref.preset:
                # Built-in preset
                spec = get_naming_strategy_spec(naming_ref.preset)
                naming_rules = spec["rules"]()
            elif naming_ref.policy_id:
                # Custom policy from DB
                policy = await self.naming_repo.get_active_policy(naming_ref.policy_id)
                if not policy:
                    raise ValueError(f"Naming policy not found or inactive: {naming_ref.policy_id}")
                naming_rules = self._load_naming_from_policy(policy)

        # Resolve guardrail
        guardrail_preset = None
        if guardrail_ref:
            if guardrail_ref.preset:
                # Built-in preset
                spec = get_guardrail_preset_spec(guardrail_ref.preset)
                # Preset class는 기본값을 가지고 있어 인자 없이 호출 가능
                guardrail_preset = spec.preset_class.model_validate({})
            elif guardrail_ref.policy_id:
                # Custom policy from DB
                policy = await self.guardrail_repo.get_active_policy(guardrail_ref.policy_id)
                if not policy:
                    raise ValueError(
                        f"Guardrail policy not found or inactive: {guardrail_ref.policy_id}"
                    )
                guardrail_preset = self._load_guardrail_from_policy(policy)

        # Create validator
        if naming_rules and guardrail_preset:
            return create_full_validator(naming_rules, guardrail_preset)
        if naming_rules:
            return create_naming_only_validator(naming_rules)
        if guardrail_preset:
            return create_guardrail_only_validator(guardrail_preset)

        return None

    def _load_naming_from_policy(self, policy: StoredPolicy) -> CustomNamingRules:
        """Load naming rules from stored policy"""
        if policy.policy_type != PolicyType.NAMING:
            raise ValueError(f"Expected naming policy, got {policy.policy_type}")

        # Convert dict to CustomNamingRules
        return CustomNamingRules(**policy.content)

    def _load_guardrail_from_policy(self, policy: StoredPolicy) -> CustomGuardrailPreset:
        """Load guardrail preset from stored policy"""
        if policy.policy_type != PolicyType.GUARDRAIL:
            raise ValueError(f"Expected guardrail policy, got {policy.policy_type}")

        # Validate required fields
        required_fields = ["preset_name", "version"]
        missing_fields = [f for f in required_fields if f not in policy.content]

        if missing_fields:
            raise ValueError(
                f"Guardrail policy '{policy.name}' (ID: {policy.policy_id}) is missing required fields: {missing_fields}. "
                f"CustomGuardrailPreset requires: preset_name (str), version (str, e.g., '1.0.0')"
            )

        # Convert dict to CustomGuardrailPreset
        return CustomGuardrailPreset(**policy.content)
