"""Naming Policy Validator

Validates topic names against naming rules.
"""

import re

from .....shared.domain.policy_types import (
    DomainPolicySeverity,
    DomainPolicyViolation,
    DomainResourceType,
)
from .rule.rule_schema import BaseNamingRules


class NamingValidator:
    """Validates topic names against naming rules"""

    def __init__(self, rules: BaseNamingRules) -> None:
        """Initialize validator with naming rules

        Args:
            rules: Naming rules to apply (Permissive/Balanced/Strict/Custom)
        """
        self.rules = rules

    def validate(self, topic_name: str) -> list[DomainPolicyViolation]:
        """Validate single topic name

        Args:
            topic_name: Topic name to validate

        Returns:
            List of violations (empty if valid)
        """
        violations: list[DomainPolicyViolation] = []

        # 1. Length validation
        if len(topic_name) < self.rules.min_length:
            violations.append(
                DomainPolicyViolation(
                    resource_type=DomainResourceType.TOPIC,
                    resource_name=topic_name,
                    rule_id="naming.min_length",
                    field="name",
                    message=f"Topic name too short (min: {self.rules.min_length}, got: {len(topic_name)})",
                    severity=DomainPolicySeverity.ERROR,
                )
            )

        if len(topic_name) > self.rules.max_length:
            violations.append(
                DomainPolicyViolation(
                    resource_type=DomainResourceType.TOPIC,
                    resource_name=topic_name,
                    rule_id="naming.max_length",
                    field="name",
                    message=f"Topic name too long (max: {self.rules.max_length}, got: {len(topic_name)})",
                    severity=DomainPolicySeverity.ERROR,
                )
            )

        # 2. Reserved words check
        if topic_name in self.rules.reserved_words:
            violations.append(
                DomainPolicyViolation(
                    resource_type=DomainResourceType.TOPIC,
                    resource_name=topic_name,
                    rule_id="naming.reserved_words",
                    field="name",
                    message=f"Topic name '{topic_name}' is reserved by Kafka",
                    severity=DomainPolicySeverity.ERROR,
                )
            )

        # 3. Forbidden prefixes check
        for prefix in self.rules.forbidden_prefixes:
            if topic_name.startswith(prefix):
                violations.append(
                    DomainPolicyViolation(
                        resource_type=DomainResourceType.TOPIC,
                        resource_name=topic_name,
                        rule_id="naming.forbidden_prefixes",
                        field="name",
                        message=f"Topic name starts with forbidden prefix '{prefix}'",
                        severity=DomainPolicySeverity.ERROR,
                    )
                )
                break

        # 4. Pattern validation
        if not re.match(self.rules.pattern, topic_name):
            violations.append(
                DomainPolicyViolation(
                    resource_type=DomainResourceType.TOPIC,
                    resource_name=topic_name,
                    rule_id="naming.pattern",
                    field="name",
                    message=f"Topic name '{topic_name}' does not match pattern: {self.rules.pattern}",
                    severity=DomainPolicySeverity.ERROR,
                )
            )

        return violations

    def validate_batch(self, topic_names: list[str]) -> list[DomainPolicyViolation]:
        """Validate multiple topic names

        Args:
            topic_names: List of topic names to validate

        Returns:
            List of all violations across all topics
        """
        all_violations: list[DomainPolicyViolation] = []

        for topic_name in topic_names:
            violations = self.validate(topic_name)
            all_violations.extend(violations)

        return all_violations
