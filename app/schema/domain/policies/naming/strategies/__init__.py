"""Schema Naming Strategies

3 Strategy Axes:
1. SR_BUILT_IN - Schema Registry built-in strategies (3 types)
2. GOV - kafka-gov extended strategies (3 types)
3. CUSTOM - User-defined strategies (YAML-based)

Structure:
- config.py - Pydantic ConfigDict settings
- schema.py - Pydantic v2 models (StrictStr + StringConstraints)
- registry.py - Strategy registry (singleton)
- validator.py - Subject validator (with security checks)

Note:
    Synchronization/classification is handled separately.
    This module focuses on validation only.
"""

from .registry import StrategyRegistry, get_registry
from .schema import (
    BaseSubjectInput,
    CompactRecordStrategyInput,
    CustomStrategyInput,
    EnvPrefixedStrategyInput,
    EnvStr,
    KeyOrValueStr,
    NamingValidationResult,
    NamingViolation,
    RecordNameStrategyInput,
    StrategyAxis,
    StrategyDescriptor,
    SubjectStr,
    TeamScopedStrategyInput,
    TeamStr,
    TopicNameStrategyInput,
    TopicRecordNameStrategyInput,
)

__all__ = [
    # Models
    "BaseSubjectInput",
    # GOV Inputs
    "CompactRecordStrategyInput",
    # CUSTOM Inputs
    "CustomStrategyInput",
    "EnvPrefixedStrategyInput",
    # Type Aliases
    "EnvStr",
    "KeyOrValueStr",
    "NamingValidationResult",
    "NamingViolation",
    # SR_BUILT_IN Inputs
    "RecordNameStrategyInput",
    # Enums
    "StrategyAxis",
    "StrategyDescriptor",
    # Registry
    "StrategyRegistry",
    "SubjectStr",
    "TeamScopedStrategyInput",
    "TeamStr",
    "TopicNameStrategyInput",
    "TopicRecordNameStrategyInput",
    "get_registry",
]
