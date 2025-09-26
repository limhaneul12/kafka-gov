"""Schema Interface 타입 힌트 정의"""

from __future__ import annotations

from typing import Annotated, Final, TypeAlias

from pydantic import Field, StrictStr, StringConstraints, TypeAdapter, conint

StrongString = Annotated[StrictStr, StringConstraints, Field]
StrongInt = Annotated[int, Field]

# 타입 별칭 정의
ChangeId: TypeAlias = str
TagName: TypeAlias = str
DocumentUrl: TypeAlias = str
ErrorSeverity: TypeAlias = str
TeamName: TypeAlias = str

COMMON_CHANGE_ID_PATTERN: Final[str] = r"^[a-zA-Z0-9_-]+$"
COMMON_TAG_NAME_PATTERN: Final[str] = r"^[a-z0-9_-]+$"
COMMON_DOCUMENT_URL_PATTERN: Final[str] = r"^https?://.*"
COMMON_ERROR_SEVERITY_PATTERN: Final[str] = r"^(error|warning)$"
COMMON_TEAM_NAME_PATTERN: Final[str] = r"^[a-z0-9-]+$"

# TypeAdapter 인스턴스들 (런타임 검증용)
change_id_adapter = TypeAdapter(ChangeId)
tag_name_adapter = TypeAdapter(TagName)
document_url_adapter = TypeAdapter(DocumentUrl)
error_severity_adapter = TypeAdapter(ErrorSeverity)
team_name_adapter = TypeAdapter(TeamName)


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
