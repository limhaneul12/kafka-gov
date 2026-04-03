"""공통 예외 베이스 클래스 — 모든 도메인 예외의 최상위 계층"""

from __future__ import annotations


class DomainError(Exception):
    """도메인 예외 베이스 — 비즈니스 규칙 위반 시 발생"""


class InfraError(Exception):
    """인프라 예외 베이스 — 외부 시스템 연동 실패 시 발생"""


class NotFoundError(DomainError):
    """리소스를 찾을 수 없을 때 발생"""

    def __init__(self, resource_type: str, resource_id: str) -> None:
        super().__init__(f"{resource_type} not found: {resource_id}")
        self.resource_type = resource_type
        self.resource_id = resource_id


class ValidationError(DomainError):
    """도메인 검증 실패 시 발생"""

    def __init__(self, message: str, field: str | None = None) -> None:
        super().__init__(message)
        self.field = field


class ConflictError(DomainError):
    """중복/충돌 발생 시"""

    def __init__(self, resource_type: str, identifier: str) -> None:
        super().__init__(f"{resource_type} already exists: {identifier}")
        self.resource_type = resource_type
        self.identifier = identifier


class AuthorizationError(DomainError):
    """권한 부족 시 발생"""

    def __init__(self, action: str, resource: str) -> None:
        super().__init__(f"not authorized to {action} on {resource}")
        self.action = action
        self.resource = resource
