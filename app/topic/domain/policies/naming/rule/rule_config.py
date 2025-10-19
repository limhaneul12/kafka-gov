"""Naming Rule ConfigDict Constants

Pydantic ConfigDict configurations for each naming strategy.
"""

from pydantic import ConfigDict

# ============================================================================
# ConfigDict Constants for Each Strategy
# ============================================================================

PERMISSIVE_CONFIG = ConfigDict(
    frozen=True,
    validate_assignment=False,
    use_enum_values=True,
    str_strip_whitespace=True,
    arbitrary_types_allowed=True,
)
"""
🎯 Permissive Strategy ConfigDict - Minimal constraints

frozen=True: Immutable object
validate_assignment=False: No validation on assignment (permissive)
use_enum_values=True: Use enum values
str_strip_whitespace=True: Strip whitespace automatically
arbitrary_types_allowed=True: Allow arbitrary types
"""

BALANCED_CONFIG = ConfigDict(
    frozen=True,
    validate_assignment=True,
    use_enum_values=True,
    str_strip_whitespace=True,
    str_to_lower=True,
)
"""
⚖️ Balanced Strategy ConfigDict - Moderate constraints

frozen=True: Immutable object
validate_assignment=True: Validate on assignment
use_enum_values=True: Use enum values
str_strip_whitespace=True: Strip whitespace automatically
str_to_lower=True: Convert strings to lowercase automatically
"""

STRICT_CONFIG = ConfigDict(
    frozen=True,
    validate_assignment=True,
    use_enum_values=True,
    str_strip_whitespace=True,
    strict=True,
    extra="forbid",
    validate_default=True,
    str_to_lower=True,
)
"""
🔥 Strict Strategy ConfigDict - Maximum constraints

frozen=True: Immutable object
validate_assignment=True: Validation on assignment required
use_enum_values=True: Use enum values
str_strip_whitespace=True: Strip whitespace automatically
strict=True: Strict type validation (prohibit automatic number conversion)
extra="forbid": Prohibit additional fields
validate_default=True: Validate default values
str_to_lower=True: Convert strings to lowercase automatically
"""

CUSTOM_CONFIG = ConfigDict(
    frozen=True,
    validate_assignment=True,
    use_enum_values=True,
    str_strip_whitespace=True,
    extra="allow",
    arbitrary_types_allowed=True,
)
"""
🎨 Custom Strategy ConfigDict - Flexible constraints

frozen=True: Immutable object
validate_assignment=True: Validate on assignment
use_enum_values=True: Use enum values
str_strip_whitespace=True: Strip whitespace automatically
extra="allow": Allow user-defined fields
arbitrary_types_allowed=True: Allow arbitrary types
"""
