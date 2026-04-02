"""도메인별 예외 클래스 패키지

각 도메인의 예외는 shared/exceptions/{domain}_exceptions.py 에서 관리한다.
도메인 모듈은 여기서 import하여 사용한다.
"""

from app.shared.exceptions.base_exceptions import (
    DomainError,
    InfraError,
    NotFoundError,
    ValidationError,
)

__all__ = [
    "DomainError",
    "InfraError",
    "NotFoundError",
    "ValidationError",
]
