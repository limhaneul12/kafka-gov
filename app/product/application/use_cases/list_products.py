"""Data Product 목록 조회 유스케이스"""

from __future__ import annotations

import logging

from app.product.domain.models.queries import ListProductsQuery, ListProductsResult
from app.product.domain.repositories.product_repository import IDataProductRepository

logger = logging.getLogger(__name__)


class ListProductsUseCase:
    """Data Product 목록 조회 — 도메인/환경/생명주기 필터링"""

    def __init__(self, repository: IDataProductRepository) -> None:
        self._repository = repository

    async def execute(self, query: ListProductsQuery) -> ListProductsResult:
        if query.domain:
            items = await self._repository.list_by_domain(
                query.domain,
                lifecycle=query.lifecycle,
                limit=query.limit,
                offset=query.offset,
            )
        elif query.environment:
            items = await self._repository.list_by_environment(
                query.environment,
                lifecycle=query.lifecycle,
                limit=query.limit,
                offset=query.offset,
            )
        else:
            items = await self._repository.list_all(
                lifecycle=query.lifecycle,
                limit=query.limit,
                offset=query.offset,
            )

        total = await self._repository.count(lifecycle=query.lifecycle)

        return ListProductsResult(
            items=items,
            total=total,
            limit=query.limit,
            offset=query.offset,
        )
