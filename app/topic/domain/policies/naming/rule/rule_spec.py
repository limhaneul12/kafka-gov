"""Naming Strategy Specifications

Strategy specifications and utility functions.
"""

from typing import Any

from .rule_schema import (
    BalancedNamingRules,
    CustomNamingRules,
    PermissiveNamingRules,
    StrictNamingRules,
)

# ============================================================================
# Topic Creation Spec Summary
# ============================================================================

NAMING_STRATEGY_SPECS: dict[str, dict[str, Any]] = {
    "permissive": {
        "name": "Permissive",
        "structure": "Free format",
        "example": "orders, user-events, MyTopic",
        "use_case": "Startup, small teams, rapid development",
        "rules": PermissiveNamingRules,
    },
    "balanced": {
        "name": "Balanced",
        "structure": "{env}.{domain}.{resource}[.{action}]",
        "example": "prod.commerce.orders.created",
        "use_case": "Mid-size companies, 3-10 teams, governance required",
        "rules": BalancedNamingRules,
    },
    "strict": {
        "name": "Strict",
        "structure": "{env}.{classification}.{domain}.{resource}.{version}",
        "example": "prod.pii.commerce.customer-data.v1",
        "use_case": "Large enterprises, regulated industries, strict compliance",
        "rules": StrictNamingRules,
    },
    "custom": {
        "name": "Custom",
        "structure": "Defined via YAML",
        "example": "Per-organization customization",
        "use_case": "Special requirements",
        "rules": CustomNamingRules,
    },
}


def get_strategy_spec(strategy_name: str) -> dict[str, Any]:
    """Get strategy specification

    Args:
        strategy_name: Strategy name (permissive, balanced, strict, custom)

    Returns:
        Strategy specification dictionary

    Raises:
        KeyError: Unknown strategy
    """
    if strategy_name not in NAMING_STRATEGY_SPECS:
        raise KeyError(
            f"Unknown strategy: {strategy_name}. "
            f"Available: {', '.join(NAMING_STRATEGY_SPECS.keys())}"
        )

    return NAMING_STRATEGY_SPECS[strategy_name]


def list_all_strategies() -> list[dict[str, Any]]:
    """List all strategies

    Returns:
        List of strategy information
    """
    return [{"strategy": name, **spec} for name, spec in NAMING_STRATEGY_SPECS.items()]
