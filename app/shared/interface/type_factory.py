"""Schema Interface 타입 힌트 정의"""

from __future__ import annotations

from typing import Annotated, Final, TypeAlias

from pydantic import Field, StrictStr, StringConstraints, TypeAdapter

# 타입 별칭 정의
ChangeId: TypeAlias = str
TagName: TypeAlias = str
DocumentUrl: TypeAlias = str
ErrorSeverity: TypeAlias = str
TeamName: TypeAlias = str


# TypeAdapter 인스턴스들 (런타임 검증용)
change_id_adapter = TypeAdapter(ChangeId)
document_url_adapter = TypeAdapter(DocumentUrl)
error_severity_adapter = TypeAdapter(ErrorSeverity)
team_name_adapter = TypeAdapter(TeamName)

COMMON_CHANGE_ID_PATTERN: Final[str] = r"^[a-zA-Z0-9_-]+$"
COMMON_TAG_NAME_PATTERN: Final[str] = r"^[a-z0-9_-]+$"
COMMON_DOCUMENT_URL_PATTERN: Final[str] = r"^https?://.*"
COMMON_ERROR_SEVERITY_PATTERN: Final[str] = r"^(error|warning)$"
COMMON_TEAM_NAME_PATTERN: Final[str] = r"^[a-z0-9-]+$"


def string_type(
    *, desc: str, max_length: int, min_length: int = 1, pattern: str | None = None
) -> type[str]:
    """문자열 타입 생성 헬퍼"""
    constraints = StringConstraints(
        min_length=min_length,
        max_length=max_length,
        pattern=pattern,
        strict=True,
        strip_whitespace=True,
    )
    return Annotated[StrictStr, constraints, Field(description=desc)]


def int_type(*, desc: str, ge: int, le: int | None = None) -> type[int]:
    """정수 타입 생성 헬퍼"""
    return Annotated[int, Field(description=desc, ge=ge, le=le, strict=True)]
