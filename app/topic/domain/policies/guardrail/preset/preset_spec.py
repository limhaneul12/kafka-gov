"""Guardrail Preset Specifications

Preset specifications and utility functions.
Follows naming's rule_spec.py structure, but enhances type safety with DTO.
"""

from dataclasses import dataclass
from typing import Any, TypeAlias

from .preset_schema import (
    BaseGuardrailPreset,
    CustomGuardrailPreset,
    DevGuardrailPreset,
    ProdGuardrailPreset,
    StgGuardrailPreset,
)

# ============================================================================
# DTO Definitions
# ============================================================================


@dataclass(frozen=True, slots=True)
class PresetSpecDTO:
    """Preset specification DTO - Type safety guaranteed

    Explicit type definition instead of dict[str, Any]
    """

    name: str
    environment: str
    description: str
    use_case: str
    preset_class: type[BaseGuardrailPreset]
    guidance: str | None = None


# Type alias for preset class union
PresetClass: TypeAlias = (
    type[DevGuardrailPreset]
    | type[StgGuardrailPreset]
    | type[ProdGuardrailPreset]
    | type[CustomGuardrailPreset]
)


# ============================================================================
# Preset Spec Summary
# ============================================================================

GUARDRAIL_PRESET_SPECS: dict[str, PresetSpecDTO] = {
    "dev": PresetSpecDTO(
        name="Development",
        environment="dev",
        description="Dev environment - minimal resources, fast iteration",
        use_case="Local development, feature testing, experimentation",
        preset_class=DevGuardrailPreset,
    ),
    "stg": PresetSpecDTO(
        name="Staging",
        environment="stg",
        description="Staging environment - production-like configuration",
        use_case="Integration testing, load testing, pre-production validation",
        preset_class=StgGuardrailPreset,
    ),
    "prod": PresetSpecDTO(
        name="Production",
        environment="prod",
        description="Production environment - high availability (minimum recommendation)",
        use_case="Production services, mission-critical data",
        preset_class=ProdGuardrailPreset,
        guidance="⚠️  Custom preset definition recommended based on business requirements",
    ),
    "custom": PresetSpecDTO(
        name="Custom",
        environment="any",
        description="User-defined preset via YAML",
        use_case="Organization-specific requirements, business-tailored settings",
        preset_class=CustomGuardrailPreset,
    ),
}


# ============================================================================
# Utility Functions
# ============================================================================


def get_preset_spec(preset_name: str) -> PresetSpecDTO:
    """Get preset specification

    Args:
        preset_name: Preset name (dev, stg, prod, custom)

    Returns:
        PresetSpecDTO object

    Raises:
        KeyError: Unknown preset
    """
    if preset_name not in GUARDRAIL_PRESET_SPECS:
        raise KeyError(
            f"Unknown preset: {preset_name}. Available: {', '.join(GUARDRAIL_PRESET_SPECS.keys())}"
        )

    return GUARDRAIL_PRESET_SPECS[preset_name]


def list_all_presets() -> list[dict[str, Any]]:
    """List all preset information

    Returns:
        List of preset information (dictionary format, uses Any for flexible structure)
    """
    return [
        {
            "preset": name,
            "name": spec.name,
            "environment": spec.environment,
            "description": spec.description,
            "use_case": spec.use_case,
            "guidance": spec.guidance,
        }
        for name, spec in GUARDRAIL_PRESET_SPECS.items()
    ]


def get_preset_class(preset_name: str) -> type[BaseGuardrailPreset]:
    """Get preset class

    Args:
        preset_name: Preset name

    Returns:
        Preset class (Pydantic BaseModel)

    Raises:
        KeyError: Unknown preset
    """
    spec = get_preset_spec(preset_name)
    return spec.preset_class


def create_preset_instance(preset_name: str, **kwargs: Any) -> BaseGuardrailPreset:
    """Create preset instance

    Args:
        preset_name: Preset name
        **kwargs: Preset creation arguments (overridable, uses Any for flexibility)

    Returns:
        Preset instance

    Raises:
        KeyError: Unknown preset
        ValidationError: Validation failed

    Example:
        >>> preset = create_preset_instance("prod")
        >>> preset.replication_factor
        3

        >>> preset = create_preset_instance("prod", replication_factor=5)
        >>> preset.replication_factor
        5
    """
    preset_class = get_preset_class(preset_name)
    return preset_class(**kwargs)


def is_builtin_preset(preset_name: str) -> bool:
    """Check if preset is built-in

    Args:
        preset_name: Preset name

    Returns:
        True if built-in, False if custom
    """
    return preset_name in {"dev", "stg", "prod"}


def get_preset_defaults(preset_name: str) -> dict[str, Any]:
    """Get preset default values

    Args:
        preset_name: Preset name

    Returns:
        Default values dictionary (uses Any for mixed types)

    Example:
        >>> defaults = get_preset_defaults("prod")
        >>> defaults["replication_factor"]
        3
    """
    preset_class = get_preset_class(preset_name)
    # Extract default values from Pydantic model
    return {
        field_name: field_info.default
        for field_name, field_info in preset_class.model_fields.items()
        if field_info.default is not None
    }
