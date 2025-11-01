"""Schema Naming Strategies - Pydantic v2 Models

3 Strategy Axes:
1. SR_BUILT_IN - Schema Registry built-in strategies (3 types)
2. GOV - kafka-gov extended strategies (3 types)
3. CUSTOM - User-defined strategies (YAML-based)
"""

import re
from abc import ABC, abstractmethod
from enum import Enum
from typing import Annotated

from pydantic import BaseModel, Field, StrictStr, StringConstraints, field_validator

from .config import CUSTOM_CONFIG, GOV_CONFIG, SR_BUILT_IN_CONFIG

# ============================================================================
# Type Aliases (StrictStr + StringConstraints)
# ============================================================================

SubjectStr = Annotated[
    StrictStr,
    StringConstraints(
        min_length=1,
        max_length=249,  # Kafka subject name limit
        pattern=r"^[a-z0-9A-Z._-]+$",  # Only safe characters
        strip_whitespace=True,
    ),
]


# Additional validation for security
def validate_subject_security(v: str) -> str:
    """Security validation for subject names

    Validates:
    - No forbidden prefixes (Confluent reserved)
    - No path traversal patterns
    - No control characters
    - No null bytes

    Raises:
        ValueError: If validation fails
    """
    # Forbidden prefixes
    if v.startswith(("_confluent", "_schemas", "__")):
        raise ValueError(f"Prefix is reserved by Confluent: {v[:20]}")

    # Path traversal
    if ".." in v or "//" in v or "\\" in v:
        raise ValueError("Path traversal patterns are not allowed")

    # Control characters
    if any(ord(c) < 32 or ord(c) == 127 for c in v):
        raise ValueError("Control characters are not allowed")

    # Null bytes
    if "\x00" in v:
        raise ValueError("Null bytes are not allowed")

    return v


EnvStr = Annotated[
    StrictStr,
    StringConstraints(
        pattern=r"^(dev|stg|prod)$",
        strip_whitespace=True,
    ),
]

KeyOrValueStr = Annotated[
    StrictStr,
    StringConstraints(
        pattern=r"^(key|value)$",
        strip_whitespace=True,
    ),
]

TeamStr = Annotated[
    StrictStr,
    StringConstraints(
        min_length=1,
        max_length=50,
        pattern=r"^[a-z0-9_-]+$",
        strip_whitespace=True,
    ),
]

# ============================================================================
# Enums
# ============================================================================


class StrategyAxis(str, Enum):
    """Strategy Axis"""

    SR_BUILT_IN = "SR_BUILT_IN"  # Schema Registry built-in
    GOV = "GOV"  # kafka-gov extended
    CUSTOM = "CUSTOM"  # User-defined (YAML-based)


# ============================================================================
# Base Models
# ============================================================================


class StrategyDescriptor(BaseModel):
    """Strategy Metadata"""

    model_config = SR_BUILT_IN_CONFIG

    id: StrictStr = Field(..., description="Unique strategy ID (e.g., builtin:TopicNameStrategy)")
    axis: StrategyAxis = Field(..., description="Strategy axis")
    key: StrictStr = Field(..., description="Strategy key (e.g., TopicNameStrategy)")
    name: StrictStr = Field(..., description="Display name")
    description: StrictStr = Field(..., description="Strategy description")
    deprecated: bool = Field(default=False, description="Whether deprecated")


class BaseSubjectInput(BaseModel, ABC):
    """Base class for subject input

    All strategy inputs must inherit from this class and implement:
    - get_strategy_axis(): Returns the strategy axis
    - build_subject(): Builds the subject name from input fields
    """

    @abstractmethod
    def get_strategy_axis(self) -> StrategyAxis:
        """Returns the strategy axis"""
        ...

    @abstractmethod
    def build_subject(self) -> str:
        """Builds the subject name from input fields

        Returns:
            str: Generated subject name

        Raises:
            ValueError: If required fields are missing or invalid
        """
        ...


# ============================================================================
# SR_BUILT_IN Strategies (3 types)
# ============================================================================


class TopicNameStrategyInput(BaseSubjectInput):
    """TopicNameStrategy Input: <topic>-<key|value>"""

    model_config = SR_BUILT_IN_CONFIG

    topic: StrictStr = Field(..., min_length=1, max_length=200, description="Topic name")
    key_or_value: KeyOrValueStr = Field(..., description="key or value")

    @field_validator("topic")
    @classmethod
    def validate_topic_pattern(cls, v: str) -> str:
        """Validate topic pattern - only safe characters"""
        if not re.match(r"^[a-z0-9A-Z._-]+$", v):
            raise ValueError(f"Invalid characters in topic: {v}")
        return v

    def get_strategy_axis(self) -> StrategyAxis:
        return StrategyAxis.SR_BUILT_IN

    def build_subject(self) -> str:
        """Build subject name"""
        return f"{self.topic}-{self.key_or_value}"


class RecordNameStrategyInput(BaseSubjectInput):
    """RecordNameStrategy Input: <namespace>.<record>"""

    model_config = SR_BUILT_IN_CONFIG

    namespace: StrictStr = Field(..., min_length=1, max_length=100, description="Namespace")
    record: StrictStr = Field(..., min_length=1, max_length=100, description="Record name")

    @field_validator("namespace", "record")
    @classmethod
    def validate_dot_separated(cls, v: str) -> str:
        """Validate Java package style (dot-separated)"""
        if not v:
            raise ValueError("must not be empty")
        # Java package style: com.company.Order
        if not all(part.isidentifier() or part.replace("_", "").isalnum() for part in v.split(".")):
            raise ValueError(f"invalid format: {v}")
        return v

    def get_strategy_axis(self) -> StrategyAxis:
        return StrategyAxis.SR_BUILT_IN

    def build_subject(self) -> str:
        """Build subject name"""
        return f"{self.namespace}.{self.record}"


class TopicRecordNameStrategyInput(BaseSubjectInput):
    """TopicRecordNameStrategy Input: <topic>-<namespace>.<record>"""

    model_config = SR_BUILT_IN_CONFIG

    topic: StrictStr = Field(..., min_length=1, max_length=200, description="Topic name")
    namespace: StrictStr = Field(..., min_length=1, max_length=100, description="Namespace")
    record: StrictStr = Field(..., min_length=1, max_length=100, description="Record name")

    @field_validator("namespace", "record")
    @classmethod
    def validate_dot_separated(cls, v: str) -> str:
        """Validate Java package style (dot-separated)"""
        if not v:
            raise ValueError("must not be empty")
        if not all(part.isidentifier() or part.replace("_", "").isalnum() for part in v.split(".")):
            raise ValueError(f"invalid format: {v}")
        return v

    def get_strategy_axis(self) -> StrategyAxis:
        return StrategyAxis.SR_BUILT_IN

    def build_subject(self) -> str:
        """Build subject name"""
        return f"{self.topic}-{self.namespace}.{self.record}"


# ============================================================================
# GOV Strategies (3 types)
# ============================================================================


class EnvPrefixedStrategyInput(BaseSubjectInput):
    """EnvPrefixed Strategy Input: <env>.<namespace>-value

    Simplified format that removes company prefix and uses -value suffix.
    Example: dev.metrics.quality-value

    Note: Avro record name (PascalCase) is NOT included in subject to maintain
    lowercase-only convention for Kafka subjects.
    """

    model_config = GOV_CONFIG

    env: EnvStr = Field(..., description="Environment (dev/stg/prod)")
    namespace: StrictStr = Field(
        ..., min_length=1, max_length=200, description="Full namespace from Avro"
    )
    topic: StrictStr | None = Field(None, description="Topic name (optional, not used in subject)")

    @field_validator("env")
    @classmethod
    def lowercase_env(cls, v: str) -> str:
        """Lowercase env field"""
        return v.lower()

    @field_validator("namespace")
    @classmethod
    def clean_and_validate_namespace(cls, v: str) -> str:
        """Clean namespace: remove common company prefixes and validate

        Examples:
            com.chiringchiring.metrics.quality -> metrics.quality
            io.acme.trading.core -> trading.core
        """
        if not v:
            raise ValueError("namespace must not be empty")

        # Remove common prefixes
        prefixes_to_remove = ["com.chiringchiring.", "io.chiringchiring.", "org.chiringchiring."]
        for prefix in prefixes_to_remove:
            if v.startswith(prefix):
                v = v[len(prefix) :]
                break

        # Validate format
        if not all(part.isidentifier() or part.replace("_", "").isalnum() for part in v.split(".")):
            raise ValueError(f"invalid namespace format: {v}")

        # Convert to lowercase for subject
        return v.lower()

    def get_strategy_axis(self) -> StrategyAxis:
        return StrategyAxis.GOV

    def build_subject(self) -> str:
        """Build subject name: {env}.{namespace}-value

        Example: dev.metrics.quality-value
        """
        return f"{self.env}.{self.namespace}-value"


class TeamScopedStrategyInput(BaseSubjectInput):
    """TeamScoped Strategy Input: <team>.<namespace>.<record>"""

    model_config = GOV_CONFIG

    team: TeamStr = Field(..., description="Team name")
    namespace: StrictStr = Field(..., min_length=1, max_length=100, description="Namespace")
    record: StrictStr = Field(..., min_length=1, max_length=100, description="Record name")

    @field_validator("team")
    @classmethod
    def lowercase_team(cls, v: str) -> str:
        """Lowercase team field"""
        return v.lower()

    @field_validator("namespace", "record")
    @classmethod
    def validate_dot_separated(cls, v: str) -> str:
        """Validate Java package style (dot-separated)"""
        if not v:
            raise ValueError("must not be empty")
        if not all(part.isidentifier() or part.replace("_", "").isalnum() for part in v.split(".")):
            raise ValueError(f"invalid format: {v}")
        return v

    def get_strategy_axis(self) -> StrategyAxis:
        return StrategyAxis.GOV

    def build_subject(self) -> str:
        """Build subject name"""
        return f"{self.team}.{self.namespace}.{self.record}"


class CompactRecordStrategyInput(BaseSubjectInput):
    """CompactRecord Input: <record> (dev/local only)"""

    model_config = GOV_CONFIG

    record: StrictStr = Field(..., min_length=1, max_length=100, description="Record name")

    def get_strategy_axis(self) -> StrategyAxis:
        return StrategyAxis.GOV

    def build_subject(self) -> str:
        """Build subject name"""
        return self.record


# ============================================================================
# CUSTOM Strategy (YAML-based)
# ============================================================================


class CustomStrategyInput(BaseSubjectInput):
    """Custom Strategy Input (YAML-based)

    Users can define custom strategies via YAML configuration:

    Example YAML:
    ```yaml
    strategy_id: custom:MyCompanyStrategy
    template: "{region}.{env}.{topic}-{record}"
    fields:
      region:
        type: string
        pattern: "^(us|eu|asia)$"
        required: true
      env:
        type: string
        pattern: "^(dev|stg|prod)$"
        required: true
      topic:
        type: string
        min_length: 1
        max_length: 200
        required: true
      record:
        type: string
        min_length: 1
        max_length: 100
        required: true
    ```

    The template uses Python format string syntax.
    Field values are validated according to their type/pattern specifications.
    """

    model_config = CUSTOM_CONFIG

    # Base fields
    strategy_id: StrictStr = Field(..., description="Custom strategy ID")
    template: StrictStr = Field(..., description="Subject template (Python format string)")

    # Dynamic fields allowed (extra="allow")
    # Field values are provided by user based on YAML field definitions

    def get_strategy_axis(self) -> StrategyAxis:
        return StrategyAxis.CUSTOM

    def build_subject(self) -> str:
        """Build subject name from template and dynamic fields

        Returns:
            str: Generated subject name

        Raises:
            ValueError: If template format is invalid or required fields are missing
        """
        # Extract dynamic fields (exclude base fields)
        dynamic_fields = {
            k: v for k, v in self.model_dump().items() if k not in ("strategy_id", "template")
        }

        try:
            return self.template.format(**dynamic_fields)
        except KeyError as e:
            raise ValueError(f"Missing required field in template: {e}") from e
        except Exception as e:
            raise ValueError(f"Invalid template format: {e}") from e


# ============================================================================
# Validation Result
# ============================================================================


class NamingViolation(BaseModel):
    """Naming Violation"""

    model_config = SR_BUILT_IN_CONFIG

    subject: SubjectStr | None = Field(None, description="Generated subject")
    rule: StrictStr = Field(..., description="Violated rule")
    message: StrictStr = Field(..., description="Violation message")
    field: StrictStr | None = Field(None, description="Violated field")


class NamingValidationResult(BaseModel):
    """Naming Validation Result"""

    model_config = SR_BUILT_IN_CONFIG

    ok: bool = Field(..., description="Validation success")
    subject: SubjectStr | None = Field(None, description="Generated subject")
    violations: tuple[NamingViolation, ...] = Field(
        default_factory=tuple, description="List of violations"
    )
    serializer_snippet: dict[str, str] | None = Field(
        None, description="Serializer configuration example"
    )

    @field_validator("subject")
    @classmethod
    def validate_subject_security(cls, v: str | None) -> str | None:
        """Apply security validation to subject"""
        if v is None:
            return v
        return validate_subject_security(v)
