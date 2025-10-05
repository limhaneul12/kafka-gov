"""Topic Interface Enum 정의"""

from __future__ import annotations

from enum import Enum


class Environment(str, Enum):
    """환경 타입"""

    DEV = "dev"
    STG = "stg"
    PROD = "prod"


class TopicAction(str, Enum):
    """토픽 액션 타입"""

    CREATE = "create"
    UPSERT = "upsert"
    UPDATE = "update"
    DELETE = "delete"


class CleanupPolicy(str, Enum):
    """토픽 정리 정책"""

    DELETE = "delete"
    COMPACT = "compact"
    COMPACT_DELETE = "compact,delete"
