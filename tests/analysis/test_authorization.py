"""Analysis Authorization 테스트"""

from __future__ import annotations

import pytest

from app.analysis.domain.authorization import validate_action
from app.shared.roles import UserRole


class TestValidateAction:
    """validate_action 함수 테스트"""

    def test_admin_can_view(self):
        """ADMIN은 view 가능"""
        # 예외 발생하지 않음
        validate_action(UserRole.ADMIN, "view")

    def test_admin_can_analyze(self):
        """ADMIN은 analyze 가능"""
        validate_action(UserRole.ADMIN, "analyze")

    def test_admin_can_link(self):
        """ADMIN은 link 가능"""
        validate_action(UserRole.ADMIN, "link")

    def test_admin_can_delete(self):
        """ADMIN은 delete 가능"""
        validate_action(UserRole.ADMIN, "delete")

    def test_unknown_action(self):
        """알 수 없는 액션"""
        with pytest.raises(ValueError, match="Unknown action"):
            validate_action(UserRole.ADMIN, "unknown_action")

    def test_viewer_can_view(self):
        """VIEWER는 view 가능"""
        validate_action(UserRole.VIEWER, "view")

    def test_viewer_cannot_delete(self):
        """VIEWER는 delete 불가"""
        with pytest.raises(PermissionError, match="does not have permission"):
            validate_action(UserRole.VIEWER, "delete")
