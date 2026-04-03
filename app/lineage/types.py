"""데이터 리니지 모듈 타입 정의"""

from __future__ import annotations

from enum import StrEnum, unique
from typing import TypeAlias

NodeId: TypeAlias = str
EdgeId: TypeAlias = str


@unique
class NodeType(StrEnum):
    """리니지 노드 유형"""

    DATA_PRODUCT = "data_product"
    SERVICE = "service"
    DATABASE = "database"
    EXTERNAL_API = "external_api"
    FILE_STORAGE = "file_storage"
    TRANSFORMATION = "transformation"


@unique
class EdgeType(StrEnum):
    """리니지 엣지 유형 — 데이터가 어떻게 흐르는가"""

    PRODUCES = "produces"
    CONSUMES = "consumes"
    DERIVES_FROM = "derives_from"
    FEEDS_INTO = "feeds_into"
    MIRRORS = "mirrors"


@unique
class LinkConfidence(StrEnum):
    """리니지 연결 신뢰도"""

    MANUAL = "manual"
    AUTO_HIGH = "auto_high"
    AUTO_LOW = "auto_low"
    INFERRED = "inferred"
