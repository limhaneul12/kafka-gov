"""사용자 역할 정의 - Kafka 거버넌스용"""

from __future__ import annotations

from enum import Enum


class UserRole(str, Enum):
    """사용자 역할 정의

    Kafka 거버넌스 시스템의 사용자 역할을 정의합니다.
    현재는 단순화를 위해 3가지 역할만 제공합니다.
    """

    # 시스템 관리자 - 모든 권한
    ADMIN = "admin"

    # 개발자 - Topic/Schema 생성/수정 권한
    DEVELOPER = "developer"

    # 뷰어 - 읽기 전용 권한
    VIEWER = "viewer"

    @property
    def description(self) -> str:
        """역할 설명"""
        descriptions = {
            UserRole.ADMIN: "시스템 관리자 - 모든 리소스에 대한 전체 권한",
            UserRole.DEVELOPER: "개발자 - Topic/Schema 생성, 수정, 삭제 권한",
            UserRole.VIEWER: "뷰어 - 읽기 전용 권한",
        }
        return descriptions[self]

    @property
    def can_create(self) -> bool:
        """생성 권한 여부"""
        return self in (UserRole.ADMIN, UserRole.DEVELOPER)

    @property
    def can_update(self) -> bool:
        """수정 권한 여부"""
        return self in (UserRole.ADMIN, UserRole.DEVELOPER)

    @property
    def can_delete(self) -> bool:
        """삭제 권한 여부"""
        return self == UserRole.ADMIN

    @property
    def can_read(self) -> bool:
        """읽기 권한 여부"""
        return True  # 모든 역할이 읽기 가능

    @classmethod
    def get_default(cls) -> UserRole:
        """기본 역할 반환 (인증 없을 때 사용)"""
        return cls.ADMIN  # MVP에서는 모든 사용자를 ADMIN으로


# 기본 사용자 (인증 없을 때)
DEFAULT_USER = "system"
DEFAULT_ROLE = UserRole.ADMIN
