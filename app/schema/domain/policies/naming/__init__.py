"""Schema Domain Policies - Naming

Subject naming strategies and validation for Schema Registry governance.

3 Strategy Axes:
1. SR_BUILT_IN - Schema Registry built-in (TopicName, RecordName, TopicRecordName)
2. GOV - kafka-gov extended (EnvPrefixed, TeamScoped, CompactRecord)
3. CUSTOM - User-defined (YAML-based)

Note:
    Synchronization/classification is handled separately outside this module.
"""

from .strategies import (
    BaseSubjectInput,
    CompactRecordStrategyInput,
    EnvPrefixedStrategyInput,
    EnvStr,
    KeyOrValueStr,
    NamingValidationResult,
    NamingViolation,
    RecordNameStrategyInput,
    StrategyAxis,
    StrategyDescriptor,
    StrategyRegistry,
    SubjectStr,
    TeamScopedStrategyInput,
    TeamStr,
    TopicNameStrategyInput,
    TopicRecordNameStrategyInput,
    get_registry,
)

__all__ = [
    # Models
    "BaseSubjectInput",
    # GOV Inputs
    "CompactRecordStrategyInput",
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
