"""공통 상수 테스트"""

import pytest

from app.shared.constants import (
    ACTION_MESSAGES,
    ActivityType,
    AuditAction,
    AuditStatus,
    AuditTarget,
    MethodType,
    format_activity_message,
)


class TestAuditStatus:
    """AuditStatus 상수 테스트"""

    def test_audit_status_values(self):
        """감사 상태 값 확인"""
        assert AuditStatus.STARTED == "STARTED"
        assert AuditStatus.COMPLETED == "COMPLETED"
        assert AuditStatus.FAILED == "FAILED"


class TestActivityType:
    """ActivityType 상수 테스트"""

    def test_activity_type_values(self):
        """활동 타입 값 확인"""
        assert ActivityType.TOPIC == "topic"
        assert ActivityType.SCHEMA == "schema"


class TestAuditAction:
    """AuditAction 상수 테스트"""

    def test_audit_action_values(self):
        """감사 액션 값 확인"""
        assert AuditAction.CREATE == "CREATE"
        assert AuditAction.UPDATE == "UPDATE"
        assert AuditAction.DELETE == "DELETE"
        assert AuditAction.ALTER == "ALTER"
        assert AuditAction.DRY_RUN == "DRY_RUN"
        assert AuditAction.APPLY == "APPLY"
        assert AuditAction.REGISTER == "REGISTER"
        assert AuditAction.UPLOAD == "UPLOAD"
        assert AuditAction.SYNC == "SYNC"


class TestAuditTarget:
    """AuditTarget 상수 테스트"""

    def test_audit_target_values(self):
        """감사 대상 값 확인"""
        assert AuditTarget.BATCH == "BATCH"
        assert AuditTarget.SINGLE == "SINGLE"
        assert AuditTarget.FILES == "FILES"
        assert AuditTarget.SCHEMA_REGISTRY == "SCHEMA_REGISTRY"
        assert AuditTarget.UNKNOWN == "UNKNOWN"


class TestMethodType:
    """MethodType 상수 테스트"""

    def test_method_type_values(self):
        """실행 방법 타입 값 확인"""
        assert MethodType.SINGLE == "SINGLE"
        assert MethodType.BATCH == "BATCH"


class TestActionMessages:
    """ACTION_MESSAGES 매핑 테스트"""

    def test_topic_messages(self):
        """Topic 메시지 매핑 확인"""
        topic_messages = ACTION_MESSAGES[ActivityType.TOPIC]
        assert topic_messages[AuditAction.CREATE] == "생성됨"
        assert topic_messages[AuditAction.UPDATE] == "수정됨"
        assert topic_messages[AuditAction.DELETE] == "삭제됨"
        assert topic_messages[AuditAction.DRY_RUN] == "검증됨"
        assert topic_messages[AuditAction.APPLY] == "적용됨"

    def test_schema_messages(self):
        """Schema 메시지 매핑 확인"""
        schema_messages = ACTION_MESSAGES[ActivityType.SCHEMA]
        assert schema_messages[AuditAction.REGISTER] == "등록됨"
        assert schema_messages[AuditAction.UPLOAD] == "업로드됨"
        assert schema_messages[AuditAction.UPDATE] == "업데이트됨"
        assert schema_messages[AuditAction.DELETE] == "삭제됨"
        assert schema_messages[AuditAction.DRY_RUN] == "검증됨"
        assert schema_messages[AuditAction.APPLY] == "적용됨"


class TestFormatActivityMessage:
    """format_activity_message 함수 테스트"""

    def test_format_topic_message(self):
        """Topic 메시지 포맷팅"""
        assert format_activity_message(ActivityType.TOPIC, AuditAction.CREATE) == "생성됨"
        assert format_activity_message(ActivityType.TOPIC, AuditAction.DELETE) == "삭제됨"

    def test_format_schema_message(self):
        """Schema 메시지 포맷팅"""
        assert format_activity_message(ActivityType.SCHEMA, AuditAction.REGISTER) == "등록됨"
        assert format_activity_message(ActivityType.SCHEMA, AuditAction.UPLOAD) == "업로드됨"

    def test_format_unknown_activity_type(self):
        """알 수 없는 활동 타입 - 기본값 반환"""
        assert format_activity_message("unknown", AuditAction.CREATE) == AuditAction.CREATE

    def test_format_unknown_action(self):
        """알 수 없는 액션 - 기본값 반환"""
        unknown_action = "UNKNOWN_ACTION"
        assert format_activity_message(ActivityType.TOPIC, unknown_action) == unknown_action

    def test_format_both_unknown(self):
        """활동 타입과 액션 모두 알 수 없음"""
        unknown = "UNKNOWN"
        assert format_activity_message("unknown_type", unknown) == unknown
