"""Kafka Connect Domain Models"""

from dataclasses import dataclass
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


@dataclass(frozen=True, slots=True)
class TaskInfo:
    """태스크 정보 - Value Object"""

    id: int
    state: TaskState
    worker_id: str
    trace: str | None = None


@dataclass(frozen=True, slots=True)
class ConnectorInfo:
    """커넥터 상세 정보 - Value Object

    Kafka Connect REST API의 응답 모델
    """

    name: str
    type: ConnectorType
    state: ConnectorState
    worker_id: str
    config: dict[str, str]
    tasks: list[TaskInfo] = None  # type: ignore
    topics: list[str] = None  # type: ignore

    # 메타데이터 (거버너스용)
    team: str | None = None
    tags: list[str] = None  # type: ignore

    def __post_init__(self) -> None:
        if self.tasks is None:
            object.__setattr__(self, "tasks", [])
        if self.topics is None:
            object.__setattr__(self, "topics", [])
        if self.tags is None:
            object.__setattr__(self, "tags", [])


@dataclass(frozen=True, slots=True)
class ConnectorPlugin:
    """커넥터 플러그인 정보 - Value Object"""

    class_name: str
    type: ConnectorType
    version: str


@dataclass(frozen=True, slots=True)
class ConnectorStatus:
    """커녅터 전체 상태 (connector + tasks) - Value Object"""

    name: str
    connector: dict[str, str]  # state, worker_id
    tasks: list[dict[str, str]]  # id, state, worker_id, trace
    type: ConnectorType


@dataclass(frozen=True, slots=True)
class ConnectorConfig:
    """커녅터 설정 - Value Object"""

    name: str
    config: dict[str, str]


@dataclass(frozen=True, slots=True)
class ConnectorValidationResult:
    """커녅터 설정 검증 결과 - Value Object"""

    name: str
    error_count: int
    groups: list[dict]
    configs: list[dict]
