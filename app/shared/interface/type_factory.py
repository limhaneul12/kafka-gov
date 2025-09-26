"""Schema Interface 타입 힌트 정의"""

from __future__ import annotations

from typing import Annotated, Final

from pydantic import Field, StrictStr, StringConstraints, conint

StrongString = Annotated[StrictStr, StringConstraints, Field]
StrongInt = Annotated[int, Field]


COMMON_CHANGE_ID_PATTERN: Final[str] = r"^[a-zA-Z0-9_-]+$"
COMMON_TAG_NAME_PATTERN: Final[str] = r"^[a-z0-9_-]+$"
COMMON_DOCUMENT_URL_PATTERN: Final[str] = r"^https?://.*"
COMMON_ERROR_SEVERITY_PATTERN: Final[str] = r"^(error|warning)$"
COMMON_TEAM_NAME_PATTERN: Final[str] = r"^[a-z0-9-]+$"


def string_type(
    *, desc: str, max_length: int, min_length: int = 1, pattern: str | None = None
) -> StrongString:
    """문자열 타입 생성 헬퍼"""
    constraints = StringConstraints(
        min_length=min_length,
        max_length=max_length,
        pattern=pattern,
        strict=True,
        strip_whitespace=True,
    )
    return Annotated[StrictStr, constraints, Field(description=desc)]


def int_type(*, desc: str, ge: int, le: int | None = None) -> StrongInt:
    """정수 타입 생성 헬퍼"""
    return Annotated[conint(ge=ge, le=le, strict=True), Field(description=desc)]
