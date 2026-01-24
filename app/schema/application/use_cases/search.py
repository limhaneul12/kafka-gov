"""Schema Search Use Case"""

from __future__ import annotations

from typing import NamedTuple

from app.schema.domain.models import DomainSchemaArtifact
from app.schema.domain.repositories.interfaces import ISchemaMetadataRepository


class SearchResult(NamedTuple):
    items: list[DomainSchemaArtifact]
    total: int


class SchemaSearchUseCase:
    """스키마 검색 유스케이스"""

    def __init__(self, metadata_repository: ISchemaMetadataRepository) -> None:
        self.metadata_repository = metadata_repository

    async def execute(
        self,
        query: str | None = None,
        owner: str | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> SearchResult:
        """스키마 검색 실행"""
        offset = (page - 1) * limit
        items, total = await self.metadata_repository.search_artifacts(
            query=query, owner=owner, limit=limit, offset=offset
        )
        return SearchResult(items=items, total=total)
