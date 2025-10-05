"""공통 상수 정의"""

from __future__ import annotations


class AuditStatus:
    """감사 로그 상태"""

    STARTED = "STARTED"
    COMPLETED = "COMPLETED"
    PARTIALLY_COMPLETED = "PARTIALLY_COMPLETED"  # 부분 성공
    FAILED = "FAILED"


class ActivityType:
    """활동 타입"""

    TOPIC = "topic"
    SCHEMA = "schema"


class AuditAction:
    """감사 액션"""

    # Topic 액션
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    ALTER = "ALTER"
    DRY_RUN = "DRY_RUN"
    APPLY = "APPLY"

    # Schema 액션
    REGISTER = "REGISTER"
    UPLOAD = "UPLOAD"
    SYNC = "SYNC"


class AuditTarget:
    """감사 대상"""

    BATCH = "BATCH"
    SINGLE = "SINGLE"
    FILES = "FILES"
    SCHEMA_REGISTRY = "SCHEMA_REGISTRY"
    UNKNOWN = "UNKNOWN"


class MethodType:
    """실행 방법 타입"""

    SINGLE = "SINGLE"
    BATCH = "BATCH"


# 활동 메시지 매핑
ACTION_MESSAGES = {
    ActivityType.TOPIC: {
        AuditAction.CREATE: "생성됨",
        AuditAction.UPDATE: "수정됨",
        AuditAction.DELETE: "삭제됨",
        AuditAction.DRY_RUN: "검증됨",
        AuditAction.APPLY: "적용됨",
    },
    ActivityType.SCHEMA: {
        AuditAction.REGISTER: "등록됨",
        AuditAction.UPLOAD: "업로드됨",
        AuditAction.UPDATE: "업데이트됨",
        AuditAction.DELETE: "삭제됨",
        AuditAction.DRY_RUN: "검증됨",
        AuditAction.APPLY: "적용됨",
    },
}


def format_activity_message(activity_type: str, action: str) -> str:
    """활동 메시지 포맷팅

    Args:
        activity_type: 활동 타입 (topic/schema)
        action: 액션

    Returns:
        포맷된 메시지 (기본값: action)
    """
    return ACTION_MESSAGES.get(activity_type, {}).get(action, action)
