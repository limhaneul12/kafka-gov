"""Kafka Connect Domain Models"""

from enum import Enum

import msgspec


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


class TaskInfo(msgspec.Struct, frozen=True):
    """태스크 정보"""

    id: int
    state: TaskState
    worker_id: str
    trace: str | None = None


class ConnectorInfo(msgspec.Struct, frozen=True):
    """커넥터 상세 정보

    Kafka Connect REST API의 응답 모델
    """

    name: str
    type: ConnectorType
    state: ConnectorState
    worker_id: str
    config: dict[str, str]
    tasks: list[TaskInfo] = []
    topics: list[str] = []

    # 메타데이터 (거버넌스용)
    team: str | None = None
    tags: list[str] = []


class ConnectorPlugin(msgspec.Struct, frozen=True):
    """커넥터 플러그인 정보"""

    class_name: str
    type: ConnectorType
    version: str


class ConnectorStatus(msgspec.Struct, frozen=True):
    """커넥터 전체 상태 (connector + tasks)"""

    name: str
    connector: dict[str, str]  # state, worker_id
    tasks: list[dict[str, str]]  # id, state, worker_id, trace
    type: ConnectorType


class ConnectorConfig(msgspec.Struct, frozen=True):
    """커넥터 설정"""

    name: str
    config: dict[str, str]


class ConnectorValidationResult(msgspec.Struct, frozen=True):
    """커넥터 설정 검증 결과"""

    name: str
    error_count: int
    groups: list[dict]
    configs: list[dict]
