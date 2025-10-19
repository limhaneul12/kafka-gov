"""Shared Audit Activity 테스트"""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone

import pytest

from app.shared.domain.models import AuditActivity


class TestAuditActivity:
    """AuditActivity 도메인 모델 테스트"""

    def test_create_audit_activity(self):
        """정상적인 감사 활동 생성"""
        now = datetime.now(timezone.utc)
        activity = AuditActivity(
            activity_type="topic",
            action="CREATE",
            target="dev.test.topic",
            message="생성됨",
            actor="test-user",
            timestamp=now,
        )

        assert activity.activity_type == "topic"
        assert activity.action == "CREATE"
        assert activity.target == "dev.test.topic"
        assert activity.message == "생성됨"
        assert activity.actor == "test-user"
        assert activity.timestamp == now

    def test_dataclass_serialization(self):
        """dataclass 직렬화 테스트"""
        now = datetime.now(timezone.utc)
        activity = AuditActivity(
            activity_type="schema",
            action="REGISTER",
            target="test-subject",
            message="등록됨",
            actor="admin",
            timestamp=now,
            metadata={"key": "value"},
        )

        # dataclasses.asdict()로 변환
        result = asdict(activity)

        assert result["activity_type"] == "schema"
        assert result["action"] == "REGISTER"
        assert result["target"] == "test-subject"
        assert result["message"] == "등록됨"
        assert result["actor"] == "admin"
        assert result["timestamp"] == now
        assert result["metadata"] == {"key": "value"}

    def test_immutable(self):
        """불변성 검증 (dataclass frozen=True)"""
        activity = AuditActivity(
            activity_type="topic",
            action="UPDATE",
            target="test",
            message="수정됨",
            actor="user",
            timestamp=datetime.now(timezone.utc),
        )

        with pytest.raises(AttributeError):  # dataclass frozen=True
            activity.action = "DELETE"  # type: ignore[misc]
