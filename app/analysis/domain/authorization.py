"""Analysis Authorization - 역할 기반 권한 검증"""

from __future__ import annotations

from ...shared.roles import UserRole


class AnalysisAuthorization:
    """Analysis 도메인 권한 검증"""

    @staticmethod
    def can_view_correlation(role: UserRole) -> bool:
        """상관관계 조회 권한"""
        return role.can_read

    @staticmethod
    def can_analyze_impact(role: UserRole) -> bool:
        """영향도 분석 권한"""
        return role.can_read

    @staticmethod
    def can_manual_link(role: UserRole) -> bool:
        """수동 연결 권한 (ADMIN, DEVELOPER만)"""
        return role.can_create

    @staticmethod
    def can_delete_correlation(role: UserRole) -> bool:
        """상관관계 삭제 권한 (ADMIN만)"""
        return role.can_delete

    @staticmethod
    def validate_action(role: UserRole, action: str) -> None:
        """액션 권한 검증 (예외 발생)"""
        permissions = {
            "view": AnalysisAuthorization.can_view_correlation,
            "analyze": AnalysisAuthorization.can_analyze_impact,
            "link": AnalysisAuthorization.can_manual_link,
            "delete": AnalysisAuthorization.can_delete_correlation,
        }

        validator = permissions.get(action)
        if not validator:
            raise ValueError(f"Unknown action: {action}")

        if not validator(role):
            raise PermissionError(
                f"Role '{role.value}' does not have permission for action '{action}'"
            )
