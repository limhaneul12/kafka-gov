"""Topic Domain Enums"""

from __future__ import annotations

from enum import Enum


class DomainEnvironment(str, Enum):
    """환경 타입"""

    DEV = "dev"
    STG = "stg"
    PROD = "prod"
    UNKNOWN = "unknown"  # 환경 무관 작업용


class DomainTopicAction(str, Enum):
    """토픽 액션 타입"""

    CREATE = "create"
    UPSERT = "upsert"
    UPDATE = "update"
    DELETE = "delete"


class DomainPlanAction(str, Enum):
    """계획 액션 타입"""

    CREATE = "CREATE"
    ALTER = "ALTER"
    DELETE = "DELETE"


class DomainCleanupPolicy(str, Enum):
    """토픽 정리 정책"""

    DELETE = "delete"
    COMPACT = "compact"
    COMPACT_DELETE = "compact,delete"
