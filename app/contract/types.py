"""Data Contract 모듈 타입 정의"""

from __future__ import annotations

from enum import StrEnum, unique


@unique
class ContractStatus(StrEnum):
    """계약 상태"""

    DRAFT = "draft"
    PROPOSED = "proposed"
    ACTIVE = "active"
    BREAKING_CHANGE = "breaking_change"
    DEPRECATED = "deprecated"
    RETIRED = "retired"


@unique
class ContractRole(StrEnum):
    """계약에서의 스키마 역할"""

    KEY = "key"
    VALUE = "value"
    HEADER = "header"
