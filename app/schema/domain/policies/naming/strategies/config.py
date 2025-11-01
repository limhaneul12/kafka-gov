"""Schema Naming Strategy ConfigDict Constants

Pydantic ConfigDict configurations for each strategy type.
"""

from pydantic import ConfigDict

# ============================================================================
# ConfigDict Constants for Each Strategy Type
# ============================================================================

SR_BUILT_IN_CONFIG = ConfigDict(
    frozen=True,
    validate_assignment=True,
    use_enum_values=True,
    str_strip_whitespace=True,
    strict=True,
    extra="ignore",
)
"""
🔹 SR_BUILT_IN Strategy ConfigDict - Schema Registry 빌트인

frozen=True: Immutable object
validate_assignment=True: Validate on assignment
use_enum_values=True: Use enum values
str_strip_whitespace=True: Strip whitespace automatically
strict=True: Strict type validation
extra="ignore": Ignore extra fields (for flexibility with multiple strategies)
"""

GOV_CONFIG = ConfigDict(
    frozen=True,
    validate_assignment=True,
    use_enum_values=True,
    str_strip_whitespace=True,
    strict=True,
    extra="ignore",
)
"""
🔹 GOV Strategy ConfigDict - kafka-gov 확장

frozen=True: Immutable object
validate_assignment=True: Validate on assignment
use_enum_values=True: Use enum values
str_strip_whitespace=True: Strip whitespace automatically
strict=True: Strict type validation
extra="ignore": Ignore extra fields (for flexibility with multiple strategies)

Note: env, team 필드는 field_validator로 개별 소문자 변환
      record 필드는 대소문자 보존 (Java class name)
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
🔹 CUSTOM Strategy ConfigDict - User-defined

frozen=True: Immutable object
validate_assignment=True: Validate on assignment
use_enum_values=True: Use enum values
str_strip_whitespace=True: Strip whitespace automatically
extra="allow": Allow user-defined fields
arbitrary_types_allowed=True: Allow arbitrary types
"""
