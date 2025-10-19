"""Connect Domain Models"""

from .types_enum import (
    ConnectorState,
    ConnectorType,
    TaskState,
)
from .value_objects import (
    ConnectorConfig,
    ConnectorInfo,
    ConnectorMetadata,
    ConnectorPlugin,
    ConnectorStatus,
    ConnectorValidationResult,
    TaskInfo,
)

__all__ = [
    # Value Objects
    "ConnectorConfig",
    "ConnectorInfo",
    # Metadata
    "ConnectorMetadata",
    "ConnectorPlugin",
    # Enums
    "ConnectorState",
    "ConnectorStatus",
    "ConnectorType",
    "ConnectorValidationResult",
    "TaskInfo",
    "TaskState",
]
