"""Analysis Authorization - 역할 기반 권한 검증"""

from ...shared.roles import UserRole


def validate_action(role: UserRole, action: str) -> None:
    """액션 권한 검증

    Args:
        role: 사용자 역할
        action: 액션 타입 ("view", "analyze", "link", "delete")

    Raises:
        ValueError: 알 수 없는 액션
        PermissionError: 권한 없음

    Note:
        MVP에서는 모든 사용자가 ADMIN이므로 실질적으로 항상 통과
    """
    action_permissions = {
        "view": role.can_read,
        "analyze": role.can_read,
        "link": role.can_create,
        "delete": role.can_delete,
    }

    if action not in action_permissions:
        raise ValueError(f"Unknown action: {action}")

    if not action_permissions[action]:
        raise PermissionError(f"Role '{role.value}' does not have permission for action '{action}'")
