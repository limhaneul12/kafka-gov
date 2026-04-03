"""카탈로그 관리 유스케이스 — 항목 등록, 검색"""

from __future__ import annotations

import logging

from app.catalog.domain.models.catalog import CatalogEntry
from app.catalog.domain.models.commands import RegisterCatalogEntryCommand
from app.catalog.domain.models.queries import SearchCatalogQuery, SearchCatalogResult
from app.catalog.domain.repositories.catalog_repository import ICatalogEntryRepository
from app.shared.domain.value_objects import Tag
from app.shared.exceptions.base_exceptions import ConflictError

logger = logging.getLogger(__name__)


class RegisterCatalogEntryUseCase:
    """카탈로그 항목 등록

    비즈니스 규칙:
    - 같은 product_id로 중복 등록 불허
    """

    def __init__(self, repository: ICatalogEntryRepository) -> None:
        self._repository = repository

    async def execute(self, command: RegisterCatalogEntryCommand) -> CatalogEntry:
        existing = await self._repository.find_by_product_id(command.product_id)
        if existing is not None:
            raise ConflictError("CatalogEntry", command.product_id)

        entry = CatalogEntry(
            product_id=command.product_id,
            display_name=command.title,
            summary=command.summary,
            domain=command.domain,
            tags=tuple(Tag(key=k, value=v) for k, v in (command.tags or [])),
            glossary_terms=tuple(command.glossary_term_ids or []),
            owner_team="platform",  # TODO: command에서 받도록 수정
        )

        await self._repository.save(entry)

        logger.info(
            "catalog_entry_registered",
            extra={
                "product_id": command.product_id,
                "title": command.title,
            },
        )
        return entry


class SearchCatalogUseCase:
    """카탈로그 검색"""

    def __init__(self, repository: ICatalogEntryRepository) -> None:
        self._repository = repository

    async def execute(self, query: SearchCatalogQuery) -> SearchCatalogResult:
        items = await self._repository.search(
            query.query,
            domain=query.domain,
            tags=query.tags,
            limit=query.limit,
            offset=query.offset,
        )

        return SearchCatalogResult(
            items=items,
            total=len(items),
            limit=query.limit,
            offset=query.offset,
        )
