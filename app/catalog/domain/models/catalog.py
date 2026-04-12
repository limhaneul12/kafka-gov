"""데이터 카탈로그 도메인 모델 — 탐색, 태그, 비즈니스 용어집

카탈로그는 조직의 모든 Data Product를 검색·분류·문서화하는 계층이다.
비즈니스 사용자가 "주문 관련 데이터가 뭐가 있지?"라고 물었을 때
답할 수 있게 하는 것이 목적이다.

기존 schema metadata 중심의 tags, doc, owner 필드를
카탈로그 도메인으로 끌어올린 것이다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from app.catalog.types import TermId, TermStatus
from app.shared.domain.value_objects import ProductId, Tag
from app.shared.exceptions.catalog_exceptions import (
    DuplicateGlossaryTermError,
    GlossaryTermNotFoundError,
)


@dataclass(frozen=True, slots=True)
class GlossaryTerm:
    """비즈니스 용어 — 조직 전체에서 통일된 데이터 용어 정의

    예: "주문(Order)" = "고객이 결제를 완료한 구매 건.
    장바구니 상태는 주문이 아님."
    """

    term_id: TermId
    name: str
    definition: str
    domain: str
    status: TermStatus = TermStatus.DRAFT
    synonyms: tuple[str, ...] = ()
    related_terms: tuple[TermId, ...] = ()
    created_by: str = ""
    created_at: datetime | None = None

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("glossary term name must not be empty")
        if not self.definition:
            raise ValueError("glossary term must have a definition")


@dataclass(frozen=True, slots=True)
class CatalogEntry:
    """카탈로그 항목 — Data Product의 검색 가능한 표현

    Data Product 자체와 별개로, 카탈로그 관점에서의 메타데이터를 담는다.
    검색 인덱싱, 태그 기반 필터링, 인기도 추적에 사용된다.
    """

    product_id: ProductId
    display_name: str
    summary: str
    tags: tuple[Tag, ...]
    glossary_terms: tuple[TermId, ...]
    domain: str
    owner_team: str
    popularity_score: float = 0.0
    last_accessed_at: datetime | None = None
    indexed_at: datetime | None = None

    @property
    def tag_keys(self) -> frozenset[str]:
        return frozenset(t.key for t in self.tags)

    def matches_query(self, query: str) -> bool:
        """간단한 텍스트 매칭 (실제 검색 엔진은 인프라 레이어에서 구현)"""
        q = query.lower()
        return (
            q in self.display_name.lower()
            or q in self.summary.lower()
            or q in self.domain.lower()
            or q in self.owner_team.lower()
            or any(q in str(t).lower() for t in self.tags)
        )


@dataclass(slots=True)
class Glossary:
    """용어집 Aggregate — 비즈니스 용어의 관리 단위"""

    terms: dict[TermId, GlossaryTerm] = field(default_factory=dict)

    def add_term(self, term: GlossaryTerm) -> None:
        for existing in self.terms.values():
            if existing.name.lower() == term.name.lower():
                raise DuplicateGlossaryTermError(term.name)
        self.terms[term.term_id] = term

    def get_term(self, term_id: TermId) -> GlossaryTerm:
        if term_id not in self.terms:
            raise GlossaryTermNotFoundError(term_id)
        return self.terms[term_id]

    def remove_term(self, term_id: TermId) -> None:
        if term_id not in self.terms:
            raise GlossaryTermNotFoundError(term_id)
        del self.terms[term_id]

    def search(self, query: str) -> list[GlossaryTerm]:
        q = query.lower()
        return [
            term
            for term in self.terms.values()
            if q in term.name.lower()
            or q in term.definition.lower()
            or any(q in syn.lower() for syn in term.synonyms)
        ]

    def terms_by_domain(self, domain: str) -> list[GlossaryTerm]:
        return [t for t in self.terms.values() if t.domain == domain]

    @property
    def approved_terms(self) -> list[GlossaryTerm]:
        return [t for t in self.terms.values() if t.status is TermStatus.APPROVED]
