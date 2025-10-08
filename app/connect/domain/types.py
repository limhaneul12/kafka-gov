"""Connect Domain Types - 타입 정의"""

from __future__ import annotations

from typing import Any, TypeAlias

from pydantic import BaseModel, Field
from typing_extensions import TypedDict

# ============================================================================
# Connector 관련 타입
# ============================================================================


class ConnectorConfigDict(TypedDict, total=False):
    """커넥터 설정 타입

    Kafka Connect는 플러그인마다 다른 설정을 가지므로
    공통 필드만 정의하고 나머지는 Any로 허용
    """

    name: str
    config: dict[str, str]  # Kafka Connect는 모든 값을 문자열로 받음


class ConnectorInfoDict(TypedDict, total=False):
    """커넥터 정보 응답 타입"""

    name: str
    type: str  # "source" | "sink"
    config: dict[str, str]
    tasks: list[TaskInfoDict]
    # Kafka Connect API가 반환하는 동적 필드들
    # (플러그인마다 다를 수 있음)


class ConnectorStatusDict(TypedDict, total=False):
    """커넥터 상태 응답 타입"""

    name: str
    connector: ConnectorStateDict
    tasks: list[TaskStatusDict]
    type: str


class ConnectorStateDict(TypedDict):
    """커넥터 상태 세부 정보"""

    state: str  # "RUNNING" | "FAILED" | "PAUSED"
    worker_id: str
    trace: str | None


class TaskInfoDict(TypedDict):
    """태스크 정보 타입"""

    connector: str
    task: int


class TaskStatusDict(TypedDict):
    """태스크 상태 타입"""

    id: int
    state: str  # "RUNNING" | "FAILED" | "PAUSED"
    worker_id: str
    trace: str | None


class ConnectorTopicsDict(TypedDict):
    """커넥터 토픽 응답 타입"""

    topics: list[str]


class PluginInfoDict(BaseModel):
    """플러그인 정보 타입"""

    class_: str = Field(..., alias="class")  # API에서는 'class'로 옴
    type: str  # "source" | "sink"
    version: str

    class Config:
        populate_by_name = True  # alias와 필드명 모두 허용


class ValidationResultDict(TypedDict):
    """설정 검증 결과 타입"""

    name: str
    error_count: int
    groups: list[str]
    configs: list[ConfigValidationDict]


class ConfigValidationDict(TypedDict, total=False):
    """개별 설정 검증 정보"""

    definition: dict[str, Any]  # 스키마 정의는 복잡하므로 Any 허용
    value: dict[str, Any]


# ============================================================================
# TypeAlias - 재사용 가능한 타입 별칭
# ============================================================================

# Kafka Connect API 응답 타입들
# (API가 반환하는 JSON 구조)
ConnectorListResponse: TypeAlias = list[str] | dict[str, ConnectorInfoDict]
ConnectorResponse: TypeAlias = ConnectorInfoDict
ConnectorConfigResponse: TypeAlias = dict[str, str]
ConnectorStatusResponse: TypeAlias = ConnectorStatusDict
TaskListResponse: TypeAlias = list[TaskInfoDict]
TaskStatusResponse: TypeAlias = TaskStatusDict
TopicsResponse: TypeAlias = ConnectorTopicsDict
PluginListResponse: TypeAlias = list[PluginInfoDict]
ValidationResponse: TypeAlias = ValidationResultDict

# 설정 타입들
ConnectorConfig: TypeAlias = dict[str, Any]  # Kafka Connect는 동적 설정 허용
PluginConfig: TypeAlias = dict[str, Any]  # 플러그인마다 다른 설정
