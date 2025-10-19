"""Connect Domain Enums"""

from __future__ import annotations

from enum import Enum


class ConnectorType(str, Enum):
    """커넥터 타입"""

    SOURCE = "source"
    SINK = "sink"
    UNKNOWN = "unknown"


class ConnectorState(str, Enum):
    """커넥터 상태"""

    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    FAILED = "FAILED"
    UNASSIGNED = "UNASSIGNED"
    UNKNOWN = "UNKNOWN"


class TaskState(str, Enum):
    """태스크 상태"""

    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    FAILED = "FAILED"
    UNASSIGNED = "UNASSIGNED"
    UNKNOWN = "UNKNOWN"
