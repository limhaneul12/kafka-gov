"""카탈로그 Query/Result — 조회 요청과 응답 불변 스키마"""

from __future__ import annotations

from dataclasses import dataclass

from app.catalog.domain.models.catalog import CatalogEntry
from app.shared.domain.value_objects import Tag


@dataclass(frozen=True, slots=True)
class SearchCatalogQuery:
    """카탈로그 검색 요청"""

    query: str
    domain: str | None = None
    tags: list[Tag] | None = None
    limit: int = 20
    offset: int = 0


@dataclass(frozen=True, slots=True)
class SearchCatalogResult:
    """카탈로그 검색 응답"""

    items: list[CatalogEntry]
    total: int
    limit: int
    offset: int
