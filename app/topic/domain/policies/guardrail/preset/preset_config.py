"""Guardrail Preset ConfigDict Constants

Pydantic ConfigDict configurations for each preset.
Follows the same structure as naming's rule_config.py.
"""

from pydantic import ConfigDict

# ============================================================================
# ConfigDict Constants for Each Preset
# ============================================================================

DEV_PRESET_CONFIG = ConfigDict(
    frozen=True,
    validate_assignment=True,
    use_enum_values=True,
    str_strip_whitespace=True,
)
"""
🔧 Dev Preset ConfigDict - Minimal constraints

frozen=True: Immutable object
validate_assignment=True: Validate on assignment
use_enum_values=True: Use enum values
str_strip_whitespace=True: Strip whitespace automatically
"""

STG_PRESET_CONFIG = ConfigDict(
    frozen=True,
    validate_assignment=True,
    use_enum_values=True,
    str_strip_whitespace=True,
    validate_default=True,
)
"""
⚙️  Stg Preset ConfigDict - Moderate constraints

frozen=True: Immutable object
validate_assignment=True: Validate on assignment
use_enum_values=True: Use enum values
str_strip_whitespace=True: Strip whitespace automatically
validate_default=True: Validate default values
"""

PROD_PRESET_CONFIG = ConfigDict(
    frozen=True,
    validate_assignment=True,
    use_enum_values=True,
    str_strip_whitespace=True,
    strict=True,
    validate_default=True,
)
"""
🔥 Prod Preset ConfigDict - Strict constraints

frozen=True: Immutable object
validate_assignment=True: Validate on assignment
use_enum_values=True: Use enum values
str_strip_whitespace=True: Strip whitespace automatically
strict=True: Strict type validation (no automatic type coercion)
validate_default=True: Validate default values
"""

CUSTOM_PRESET_CONFIG = ConfigDict(
    frozen=True,
    validate_assignment=True,
    use_enum_values=True,
    str_strip_whitespace=True,
    extra="allow",
    arbitrary_types_allowed=True,
)
"""
🎨 Custom Preset ConfigDict - Flexible constraints

frozen=True: Immutable object
validate_assignment=True: Validate on assignment
use_enum_values=True: Use enum values
str_strip_whitespace=True: Strip whitespace automatically
extra="allow": Allow user-defined fields (enables YAML extensibility)
arbitrary_types_allowed=True: Allow arbitrary types (enables Any usage in metadata)
"""
