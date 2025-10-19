"""YAML Configuration Loader

Common YAML loading utilities for configuration management.
"""

from pathlib import Path
from typing import Any, TypeVar

import yaml
from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)


def load_yaml_file(file_path: str | Path) -> dict[str, Any]:
    """Load YAML file and return as dictionary

    Args:
        file_path: Path to YAML file

    Returns:
        Dictionary containing YAML data

    Raises:
        FileNotFoundError: If file doesn't exist
        yaml.YAMLError: If YAML parsing fails
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"YAML file not found: {file_path}")

    if not path.is_file():
        raise ValueError(f"Path is not a file: {file_path}")

    with open(path, encoding="utf-8") as f:
        try:
            data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise yaml.YAMLError(f"Failed to parse YAML file {file_path}: {e}") from e

    if not isinstance(data, dict):
        raise ValueError(f"YAML file must contain a dictionary at root level: {file_path}")

    return data


def load_pydantic_from_yaml[T: BaseModel](file_path: str | Path, model_class: type[T]) -> T:
    """Load Pydantic model from YAML file

    Args:
        file_path: Path to YAML file
        model_class: Pydantic model class to instantiate

    Returns:
        Instance of model_class

    Raises:
        FileNotFoundError: If file doesn't exist
        yaml.YAMLError: If YAML parsing fails
        ValidationError: If data doesn't match model schema

    Example:
        >>> from app.topic.domain.policies.naming.rule_schema import CustomNamingRules
        >>> rules = load_pydantic_from_yaml("config/naming/custom.yaml", CustomNamingRules)
    """
    data = load_yaml_file(file_path)

    try:
        return model_class(**data)
    except ValidationError as e:
        # Pydantic ValidationError - pyrefly 타입 체커가 시그니처를 인식하지 못함
        model_name: str = model_class.__name__  # pyrefly: ignore
        raise ValidationError(  # pyrefly: ignore
            f"Failed to validate YAML data against {model_name}: {e}",
            model=model_class,  # pyrefly: ignore
        ) from e


def save_pydantic_to_yaml(model: BaseModel, file_path: str | Path) -> None:
    """Save Pydantic model to YAML file

    Args:
        model: Pydantic model instance
        file_path: Path to save YAML file

    Raises:
        OSError: If file cannot be written

    Example:
        >>> from app.topic.domain.policies.guardrail.preset_schema import CustomGuardrailPreset
        >>> preset = CustomGuardrailPreset(...)
        >>> save_pydantic_to_yaml(preset, "config/guardrails/my_preset.yaml")
    """
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Convert Pydantic model to dict
    data = model.model_dump(exclude_none=True, mode="python")

    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(
            data,
            f,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )
