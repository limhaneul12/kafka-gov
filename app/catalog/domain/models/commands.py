"""카탈로그 Command — 도메인 의도를 표현하는 불변 스키마"""

from __future__ import annotations

from dataclasses import dataclass

from app.catalog.types import TermId, TermStatus
from app.shared.types import DomainName, ProductId


@dataclass(frozen=True, slots=True)
class RegisterCatalogEntryCommand:
    """카탈로그 항목 등록 요청"""

    product_id: ProductId
    title: str
    summary: str
    domain: DomainName
    tags: list[tuple[str, str]] | None = None
    glossary_term_ids: list[TermId] | None = None


@dataclass(frozen=True, slots=True)
class CreateGlossaryTermCommand:
    """용어집 용어 생성 요청"""

    name: str
    definition: str
    domain: DomainName
    synonyms: list[str] | None = None
    related_term_ids: list[TermId] | None = None


@dataclass(frozen=True, slots=True)
class UpdateTermStatusCommand:
    """용어 상태 변경 요청"""

    term_id: TermId
    new_status: TermStatus
