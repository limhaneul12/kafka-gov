"""Topic Naming Rules - 3 Built-in Strategies + Custom

Each strategy defines topic creation specifications.
"""

import re
from typing import Annotated

from pydantic import BaseModel, Field, StrictStr, StringConstraints, field_validator

from app.topic.domain.policies.naming.rule.rule_config import (
    BALANCED_CONFIG,
    CUSTOM_CONFIG,
    PERMISSIVE_CONFIG,
    STRICT_CONFIG,
)

# ============================================================================
# Common Settings and Base Class
# ============================================================================

# 🔥 Type aliases using StringConstraints (for Strict strategy)
VersionStr = Annotated[StrictStr, StringConstraints(pattern=r"^v[0-9]+$", strict=True)]
ClassificationStr = Annotated[
    StrictStr, StringConstraints(pattern=r"^(pii|public|internal)$", strict=True)
]
EnvironmentStr = Annotated[StrictStr, StringConstraints(pattern=r"^(dev|stg|prod)$", strict=True)]
StrictPrefixStr = Annotated[StrictStr, StringConstraints(min_length=1, max_length=50, strict=True)]


class BaseNamingRules(BaseModel):
    """Base class for naming rules

    Defines common fields required by all strategies.
    ConfigDict is defined individually in each strategy.
    """

    # Common field: Pattern
    pattern: str = Field(min_length=1, description="Naming pattern (regex)")

    # Common field: Forbidden prefixes
    forbidden_prefixes: list[str] = Field(
        default_factory=list, description="List of forbidden prefixes"
    )

    # Common field: Reserved words (Kafka internal topics)
    reserved_words: list[str] = Field(
        default_factory=lambda: [
            "__consumer_offsets",
            "__transaction_state",
            "_schemas",
            "connect-configs",
            "connect-offsets",
            "connect-status",
        ],
        description="Kafka reserved words",
    )

    # Common field: Length limits (Kafka constraint)
    min_length: int = Field(default=1, ge=1, le=249, description="Minimum topic name length")
    max_length: int = Field(
        default=249, ge=1, le=249, description="Maximum topic name length (Kafka limit: 249)"
    )


# ============================================================================
# Built-in Strategy 1: Permissive
# ============================================================================


class PermissiveNamingRules(BaseNamingRules):
    """Permissive naming rules - For Startup/Small Team

    Topic creation spec:
        Structure: Free format
        Constraints: Only Kafka reserved words prohibited

    Allowed examples:
        ✅ orders
        ✅ user-events
        ✅ MyTopic
        ✅ PROD_ORDERS
        ✅ analytics.page_views

    Prohibited examples:
        ❌ __consumer_offsets (reserved word)
        ❌ __transaction_state (reserved word)
        ❌ [over 249 chars] (Kafka limit)
    """

    """
    🎯 Permissive-specific ConfigDict - Minimal constraints
    
    frozen=True: Immutable object
    validate_assignment=False: No validation on assignment (permissive)
    use_enum_values=True: Use enum values
    str_strip_whitespace=True: Strip whitespace automatically
    arbitrary_types_allowed=True: Allow arbitrary types
    """
    model_config = PERMISSIVE_CONFIG

    # Allow almost all characters (uppercase, lowercase, numbers, ._-)
    pattern: str = r"^[a-zA-Z0-9._-]+$"

    # No forbidden prefixes (override)
    forbidden_prefixes: list[str] = Field(default_factory=list)


# ============================================================================
# Built-in Strategy 2: Balanced
# ============================================================================


class BalancedNamingRules(BaseNamingRules):
    """Balanced naming rules - For Mid-size Company

    Topic creation spec:
        Structure: {environment}.{domain}.{resource}[.{action}]
        Constraints:
            - Environment prefix required (dev, stg, prod)
            - Only lowercase + numbers + ._- allowed
            - Temporary/test topics prohibited (by environment)

    Allowed examples:
        ✅ dev.commerce.orders
        ✅ stg.marketing.campaigns.sent
        ✅ prod.analytics.events.processed
        ✅ prod.payments.transactions.v1

    Prohibited examples:
        ❌ orders (no environment prefix)
        ❌ prod.TMP.test (uppercase used)
        ❌ prod.test.something (test prefix prohibited)
        ❌ dev.commerce.ORDERS (uppercase used)
    """

    model_config = BALANCED_CONFIG

    # Structure: {env}.{domain}.{resource}...
    pattern: str = r"^(dev|stg|prod)\.[a-z0-9]+\.[a-z0-9._-]+$"

    # Environment-specific forbidden prefixes (override)
    forbidden_prefixes: list[str] = Field(
        default_factory=lambda: [
            "tmp.",
            "test.",
            "debug.",
            "temp.",
            "scratch.",
        ],
        description="Environment-specific forbidden prefixes",
    )

    # Environment list (additional field)
    allowed_environments: list[str] = Field(
        default_factory=lambda: ["dev", "stg", "prod"],
        description="Allowed environment list",
    )


# ============================================================================
# Common Validation Functions
# ============================================================================


def _validate_no_duplicates(values: list, error_message: str) -> list:
    """Common function to validate list for duplicates

    Args:
        values: List to validate
        error_message: Error message if duplicates found

    Returns:
        Original list (if no duplicates)

    Raises:
        ValueError: If duplicates exist
    """
    unique = list(dict.fromkeys(values))
    if len(unique) != len(values):
        raise ValueError(error_message)
    return values


# ============================================================================
# Built-in Strategy 3: Strict
# ============================================================================


class StrictNamingRules(BaseNamingRules):
    """Strict naming rules - For Enterprise/Compliance

    Topic creation spec:
        Structure: {env}.{classification}.{domain}.{resource}.{version}
        Constraints:
            - All fields required
            - Data classification required (pii, public, internal)
            - Version required (v1, v2, ...)
            - Strict type validation (StrictStr)
            - Additional fields prohibited

    Allowed examples:
        ✅ prod.pii.commerce.customer-data.v1
        ✅ prod.public.analytics.page-views.v2
        ✅ dev.internal.marketing.campaigns.v1
        ✅ stg.pii.payments.transactions.v3

    Prohibited examples:
        ❌ prod.commerce.orders (no classification/version)
        ❌ prod.unknown.commerce.orders.v1 (invalid classification)
        ❌ prod.pii.commerce.orders (no version)
        ❌ prod.pii.Commerce.orders.v1 (uppercase used)
        ❌ prod.pii.commerce.test-data.v1 (test prefix prohibited)
    """

    model_config = STRICT_CONFIG

    # 🔥 Using StrictStr - Only strings allowed (no automatic number conversion)
    pattern: StrictStr = Field(
        default=r"^(dev|stg|prod)\.(pii|public|internal)\.[a-z0-9]+\.[a-z0-9-]+\.v[0-9]+$",
        description="Strict topic naming pattern",
    )

    # 🔥 Using StringConstraints - Forbidden prefixes (stricter, override)
    forbidden_prefixes: list[StrictPrefixStr] = Field(
        default_factory=lambda: [
            "tmp.",
            "test.",
            "debug.",
            "temp.",
            "scratch.",
            "draft.",
            "experimental.",
        ],
        description="List of forbidden prefixes (each 1-50 chars, strict validation)",
    )

    # 🔥 Using StringConstraints - Reserved words (override)
    reserved_words: list[StrictPrefixStr] = Field(
        default_factory=lambda: [
            "__consumer_offsets",
            "__transaction_state",
            "_schemas",
            "connect-configs",
            "connect-offsets",
            "connect-status",
        ],
        description="Kafka reserved words (each 1-50 chars, strict validation)",
    )

    # 🔥 Using StringConstraints - Data classifications (required validation)
    data_classifications: list[ClassificationStr] = Field(
        default_factory=lambda: ["pii", "public", "internal"],
        description="Allowed data classification list (only pii|public|internal)",
    )

    # 🔥 Using StringConstraints - Environment list
    allowed_environments: list[EnvironmentStr] = Field(
        default_factory=lambda: ["dev", "stg", "prod"],
        description="Allowed environment list (only dev|stg|prod)",
    )

    # 🔥 Using StringConstraints - Version pattern
    version_pattern: VersionStr = Field(
        default="v1", description="Version format (only v1, v2, v3... allowed)"
    )

    # Version required
    require_version: bool = Field(default=True, description="Whether version is required")

    # Data classification required
    require_classification: bool = Field(
        default=True, description="Whether data classification is required"
    )

    @field_validator("data_classifications")
    @classmethod
    def validate_classifications(cls, v: list[ClassificationStr]) -> list[ClassificationStr]:
        """Validate data classifications"""
        if not v:
            raise ValueError("At least one data classification is required")

        # Duplicate validation (reuse common function)
        return _validate_no_duplicates(v, "Duplicate data classifications found")

    @field_validator("forbidden_prefixes", "reserved_words")
    @classmethod
    def validate_no_duplicates(cls, v: list[StrictPrefixStr]) -> list[StrictPrefixStr]:
        """Duplicate validation (reuse common function)"""
        return _validate_no_duplicates(v, "Duplicate values found")


# ============================================================================
# Custom Strategy (YAML-based)
# ============================================================================


class CustomNamingRules(BaseNamingRules):
    """Custom naming rules - Defined via YAML

    Rules defined by users via YAML file upload.

    YAML example:
        ```yaml
        pattern: "^(dev|prod)\\.mycompany\\.[a-z0-9-]+$"
        forbidden_prefixes:
          - tmp.
          - test.
        reserved_words:
          - __consumer_offsets
          - __transaction_state
        description: "MyCompany naming rules"
        examples:
          - "dev.mycompany.orders"
          - "prod.mycompany.users"
        ```
    """

    model_config = CUSTOM_CONFIG

    # User-defined metadata (additional fields)
    description: str | None = Field(default=None, max_length=500, description="Policy description")
    examples: list[str] = Field(default_factory=list, description="Example topic names")
    author: str | None = Field(default=None, max_length=100, description="Author")
    version: str | None = Field(default=None, max_length=20, description="Policy version")

    @field_validator("pattern")
    @classmethod
    def validate_pattern(cls, v: str) -> str:
        """Validate regex pattern"""

        try:
            re.compile(v)
        except re.error as e:
            raise ValueError(f"Invalid regex pattern: {e}") from e
        return v
