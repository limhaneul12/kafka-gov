"""Schema Domain Policies

Policy framework for schema governance (Naming only).

Structure:
- naming/ - Subject naming strategies and validation

Note:
    Unlike Topic policies, Schema policies focus only on naming.
    No guardrail or management modules (Schema creation rules are excluded).

    SchemaPolicyEngine is in policy_engine.py (renamed to avoid circular import with this package)
"""

from .naming import (
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
    # Naming
    "BaseSubjectInput",
    "CompactRecordStrategyInput",
    "EnvPrefixedStrategyInput",
    "EnvStr",
    "KeyOrValueStr",
    "NamingValidationResult",
    "NamingViolation",
    "RecordNameStrategyInput",
    "StrategyAxis",
    "StrategyDescriptor",
    "StrategyRegistry",
    "SubjectStr",
    "TeamScopedStrategyInput",
    "TeamStr",
    "TopicNameStrategyInput",
    "TopicRecordNameStrategyInput",
    "get_registry",
]
