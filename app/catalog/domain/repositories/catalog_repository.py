"""데이터 카탈로그 리포지토리 포트 — 도메인이 인프라에 요구하는 인터페이스"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.catalog.domain.models.catalog import CatalogEntry, GlossaryTerm
from app.catalog.types import TermId
from app.shared.domain.value_objects import Tag
from app.shared.types import ProductId


class ICatalogEntryRepository(ABC):
    """카탈로그 항목 영속성 포트"""

    @abstractmethod
    async def save(self, entry: CatalogEntry) -> None:
        """카탈로그 항목을 저장(생성 또는 갱신)한다."""

    @abstractmethod
    async def find_by_product_id(self, product_id: ProductId) -> CatalogEntry | None:
        """Data Product ID로 카탈로그 항목을 조회한다."""

    @abstractmethod
    async def search(
        self,
        query: str,
        *,
        domain: str | None = None,
        tags: list[Tag] | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[CatalogEntry]:
        """텍스트 검색으로 카탈로그 항목을 조회한다."""

    @abstractmethod
    async def list_by_domain(
        self,
        domain: str,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[CatalogEntry]:
        """도메인별 카탈로그 항목 목록을 조회한다."""

    @abstractmethod
    async def delete(self, product_id: ProductId) -> None:
        """카탈로그 항목을 삭제한다."""


class IGlossaryRepository(ABC):
    """용어집 영속성 포트"""

    @abstractmethod
    async def save(self, term: GlossaryTerm) -> None:
        """용어를 저장(생성 또는 갱신)한다."""

    @abstractmethod
    async def find_by_id(self, term_id: TermId) -> GlossaryTerm | None:
        """ID로 용어를 조회한다."""

    @abstractmethod
    async def search(self, query: str) -> list[GlossaryTerm]:
        """텍스트 검색으로 용어를 조회한다."""

    @abstractmethod
    async def list_by_domain(self, domain: str) -> list[GlossaryTerm]:
        """도메인별 용어 목록을 조회한다."""

    @abstractmethod
    async def list_all(self) -> list[GlossaryTerm]:
        """전체 용어 목록을 조회한다."""

    @abstractmethod
    async def delete(self, term_id: TermId) -> None:
        """용어를 삭제한다."""
