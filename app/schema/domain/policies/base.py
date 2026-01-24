"""Schema Lint Policy Interfaces"""

from abc import ABC, abstractmethod
from typing import Any

from app.schema.domain.models.lint import LintViolation


class ISchemaLintPolicy(ABC):
    """스키마 린트 정책 인터페이스"""

    @property
    @abstractmethod
    def code(self) -> str:
        """정책 코드"""

    @abstractmethod
    def check(self, schema_dict: dict[str, Any]) -> list[LintViolation]:
        """스키마 딕셔너리를 검사하여 위반 사항 목록 반환

        Note:
            Any 사용 이유: Avro 스키마 딕셔너리는 중첩된 구조(dict[str, Any])를 가지며,
            필드 타입이나 속성값이 문자열, 정수, 리스트, 또는 또 다른 딕셔너리가 될 수 있어
            정적 타입으로 특정하기 어렵습니다.
        """
