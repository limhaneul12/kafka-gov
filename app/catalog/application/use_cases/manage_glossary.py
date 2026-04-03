"""용어집 관리 유스케이스 — 용어 생성, 상태 변경, 조회"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime

from app.catalog.domain.models.catalog import GlossaryTerm
from app.catalog.domain.models.commands import (
    CreateGlossaryTermCommand,
    UpdateTermStatusCommand,
)
from app.catalog.domain.repositories.catalog_repository import IGlossaryRepository
from app.catalog.types import TermStatus
from app.shared.exceptions.catalog_exceptions import GlossaryTermNotFoundError

logger = logging.getLogger(__name__)


class CreateGlossaryTermUseCase:
    """용어집 용어 생성"""

    def __init__(self, repository: IGlossaryRepository) -> None:
        self._repository = repository

    async def execute(self, command: CreateGlossaryTermCommand) -> GlossaryTerm:
        term = GlossaryTerm(
            term_id=f"gt-{uuid.uuid4().hex[:12]}",
            name=command.name,
            definition=command.definition,
            domain=command.domain,
            status=TermStatus.DRAFT,
            synonyms=command.synonyms or [],
            related_term_ids=command.related_term_ids or [],
            created_at=datetime.now(),
        )

        await self._repository.save(term)

        logger.info(
            "glossary_term_created",
            extra={"term_id": term.term_id, "name": command.name},
        )
        return term


class UpdateTermStatusUseCase:
    """용어 상태 변경 (DRAFT → APPROVED → DEPRECATED)"""

    def __init__(self, repository: IGlossaryRepository) -> None:
        self._repository = repository

    async def execute(self, command: UpdateTermStatusCommand) -> GlossaryTerm:
        term = await self._repository.find_by_id(command.term_id)
        if term is None:
            raise GlossaryTermNotFoundError(command.term_id)

        updated = GlossaryTerm(
            term_id=term.term_id,
            name=term.name,
            definition=term.definition,
            domain=term.domain,
            status=command.new_status,
            synonyms=term.synonyms,
            related_term_ids=term.related_term_ids,
            created_at=term.created_at,
            updated_at=datetime.now(),
        )

        await self._repository.save(updated)

        logger.info(
            "glossary_term_status_changed",
            extra={
                "term_id": command.term_id,
                "new_status": command.new_status,
            },
        )
        return updated


class ListGlossaryTermsUseCase:
    """용어 목록 조회"""

    def __init__(self, repository: IGlossaryRepository) -> None:
        self._repository = repository

    async def execute(self, domain: str | None = None) -> list[GlossaryTerm]:
        if domain:
            return await self._repository.list_by_domain(domain)
        return await self._repository.list_all()
