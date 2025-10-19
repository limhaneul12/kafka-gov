"""Guardrail Presets - 3 Built-in Presets + Custom

Each preset defines topic configuration specifications.
Follows the structure of naming's rule_schema.py.
"""

from typing import Any

from pydantic import BaseModel, Field, field_validator

from .preset_config import (
    CUSTOM_PRESET_CONFIG,
    DEV_PRESET_CONFIG,
    PROD_PRESET_CONFIG,
    STG_PRESET_CONFIG,
)

# ============================================================================
# Common Settings and Base Class
# ============================================================================


class BaseGuardrailPreset(BaseModel):
    """Base class for guardrail presets

    Defines common fields required by all presets.
    ConfigDict is defined individually in each preset.
    """

    # Replication settings
    replication_factor: int = Field(ge=1, le=10, description="Replication factor (1-10)")
    min_insync_replicas: int | None = Field(
        default=None, ge=1, le=10, description="min.insync.replicas (1-10)"
    )

    # Partitions
    partitions: int = Field(ge=1, le=1000, description="Number of partitions (1-1000)")

    # Retention policy
    retention_ms: int | None = Field(
        default=None, ge=-1, description="Retention period in milliseconds (-1=infinite)"
    )

    # Cleanup policy
    cleanup_policy: str = Field(
        default="delete",
        pattern=r"^(delete|compact|delete,compact)$",
        description="Cleanup policy: delete | compact | delete,compact",
    )

    # Metadata
    description: str = Field(default="", max_length=500, description="Preset description")


# ============================================================================
# Built-in Preset 1: Development
# ============================================================================


class DevGuardrailPreset(BaseGuardrailPreset):
    """Development environment preset - Fast iteration

    Characteristics:
        - Minimal resource usage
        - Fast iteration support
        - Short retention period

    Recommended use cases:
        ✅ Local development
        ✅ Feature testing
        ✅ Experimentation

    Default settings:
        - RF=1, Partitions=3, Retention=1day
    """

    model_config = DEV_PRESET_CONFIG

    # Development environment defaults
    replication_factor: int = Field(default=1, ge=1, le=2, description="Replication factor (1-2)")
    min_insync_replicas: int | None = Field(default=None, description="min.insync.replicas")
    partitions: int = Field(default=3, ge=1, le=10, description="Number of partitions (1-10)")
    retention_ms: int | None = Field(default=86400000, description="Retention 1 day")
    cleanup_policy: str = Field(default="delete", description="Cleanup policy")
    description: str = Field(
        ...,
        description="Preset description Dev environment - minimal resources, fast iteration",
    )


# ============================================================================
# Built-in Preset 2: Staging
# ============================================================================


class StgGuardrailPreset(BaseGuardrailPreset):
    """Staging environment preset - Production-like configuration

    Characteristics:
        - Production-like configuration
        - Performance/load testing capable
        - Appropriate durability

    Recommended use cases:
        ✅ Integration testing
        ✅ Load testing
        ✅ Pre-production validation

    Default settings:
        - RF=2, ISR=1, Partitions=6, Retention=3days
    """

    model_config = STG_PRESET_CONFIG

    # Staging environment defaults
    replication_factor: int = Field(default=2, ge=2, le=3, description="Replication factor (2-3)")
    min_insync_replicas: int | None = Field(default=1, ge=1, description="min.insync.replicas")
    partitions: int = Field(default=6, ge=1, le=50, description="Number of partitions (1-50)")
    retention_ms: int | None = Field(default=259200000, description="Retention 3 days")
    cleanup_policy: str = Field(default="delete", description="Cleanup policy")
    description: str = Field(
        ...,
        description="Preset description Staging environment - production-like configuration",
    )


# ============================================================================
# Built-in Preset 3: Production
# ============================================================================


class ProdGuardrailPreset(BaseGuardrailPreset):
    """Production environment preset - High availability (minimum recommendation)

    Characteristics:
        - High availability
        - Data durability guarantee
        - Compliance capable

    Recommended use cases:
        ✅ Production services
        ✅ Mission-critical data
        ✅ Customer-facing systems

    ⚠️  Note:
        This is the minimum recommendation.
        Custom preset definition is recommended based on actual business requirements.

    Default settings:
        - RF=3, ISR=2, Partitions=12, Retention=7days
    """

    model_config = PROD_PRESET_CONFIG

    # Production environment defaults
    replication_factor: int = Field(default=3, ge=3, le=7, description="Replication factor (3-7)")
    min_insync_replicas: int | None = Field(
        default=2, ge=2, description="min.insync.replicas (>=2)"
    )
    partitions: int = Field(default=12, ge=1, le=100, description="Number of partitions (1-100)")
    retention_ms: int | None = Field(default=604800000, description="Retention 7 days")
    cleanup_policy: str = Field(default="delete", description="Cleanup policy")
    description: str = Field(
        ...,
        description="Preset description Production environment - high availability and durability (minimum recommendation)",
    )

    @field_validator("replication_factor")
    @classmethod
    def validate_replication_factor(cls, v: int) -> int:
        """Production minimum is 3"""
        if v < 3:
            raise ValueError("Production replication factor must be >= 3")
        return v

    @field_validator("min_insync_replicas")
    @classmethod
    def validate_min_insync_replicas(cls, v: int | None) -> int | None:
        """Production minimum is 2"""
        if v is not None and v < 2:
            raise ValueError("Production min.insync.replicas must be >= 2")
        return v


# ============================================================================
# Custom Preset (YAML definition)
# ============================================================================


class CustomGuardrailPreset(BaseGuardrailPreset):
    """Custom guardrail preset - Defined via YAML

    Same philosophy as naming's CustomNamingRules.
    Can be defined via YAML according to organizational requirements.

    YAML example:
        ```yaml
        preset_name: financial_critical
        version: "1.0.0"
        author: platform-team

        replication_factor: 5
        min_insync_replicas: 3
        partitions: 24
        retention_ms: 2592000000  # 30 days
        cleanup_policy: delete

        description: "Mission-critical settings for financial services"

        metadata:
          sla_target: 99.99
          compliance: ["PCI-DSS", "SOC2"]

        tags:
          - financial
          - critical
        ```
    """

    model_config = CUSTOM_PRESET_CONFIG

    # Custom-specific required fields
    preset_name: str = Field(
        min_length=1,
        max_length=100,
        description="Preset name (alphanumeric, -, _ allowed)",
    )
    version: str = Field(
        pattern=r"^\d+\.\d+\.\d+$",
        description="Semantic version (e.g., 1.0.0)",
    )

    # Custom-specific optional fields
    author: str | None = Field(default=None, max_length=100, description="Preset author")
    created_at: str | None = Field(default=None, description="Creation timestamp (ISO 8601)")
    updated_at: str | None = Field(default=None, description="Last update timestamp (ISO 8601)")

    # Additional metadata (freely extensible in YAML using Any type for flexibility)
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="User-defined metadata (Any type allows flexible YAML structure)",
    )
    tags: list[str] = Field(default_factory=list, max_length=10, description="Tags (max 10)")

    # Version management
    changelog: str | None = Field(default=None, max_length=1000, description="Change history")
    deprecated: bool = Field(default=False, description="Deprecation status")
    migration_guide: str | None = Field(
        default=None, max_length=1000, description="Migration guide"
    )

    @field_validator("preset_name")
    @classmethod
    def validate_preset_name(cls, v: str) -> str:
        """Validate preset name (alphanumeric with _ or - only)"""
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError("Preset name must be alphanumeric with _ or - only")
        return v

    @field_validator("version")
    @classmethod
    def validate_version(cls, v: str) -> str:
        """Validate semantic versioning"""
        parts = v.split(".")
        if len(parts) != 3 or not all(p.isdigit() for p in parts):
            raise ValueError("Version must follow semantic versioning (e.g., 1.0.0)")
        return v

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: list[str]) -> list[str]:
        """Validate tag count and duplicates"""
        if len(v) > 10:
            raise ValueError("Maximum 10 tags allowed")
        if len(v) != len(set(v)):
            raise ValueError("Duplicate tags found")
        return v
