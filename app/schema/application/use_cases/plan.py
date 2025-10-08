"""스키마 계획 조회 유스케이스"""

from __future__ import annotations

from ...domain.models import ChangeId, DomainSchemaPlan
from ...domain.repositories.interfaces import ISchemaMetadataRepository


class SchemaPlanUseCase:
    """스키마 계획 조회 유스케이스"""

    def __init__(self, metadata_repository: ISchemaMetadataRepository) -> None:
        self.metadata_repository = metadata_repository

    async def execute(self, change_id: ChangeId) -> DomainSchemaPlan | None:
        return await self.metadata_repository.get_plan(change_id)
