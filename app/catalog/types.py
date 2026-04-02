"""데이터 카탈로그 모듈 타입 정의"""

from __future__ import annotations

from enum import StrEnum, unique
from typing import TypeAlias

TermId: TypeAlias = str


@unique
class TermStatus(StrEnum):
    """용어 상태"""

    DRAFT = "draft"
    APPROVED = "approved"
    DEPRECATED = "deprecated"
