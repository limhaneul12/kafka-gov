"""데이터 카탈로그 도메인 예외"""

from __future__ import annotations

from app.shared.exceptions.base_exceptions import DomainError, NotFoundError


class CatalogError(DomainError):
    """카탈로그 도메인 예외 베이스"""


class GlossaryTermNotFoundError(NotFoundError):
    """용어집 항목을 찾을 수 없음"""

    def __init__(self, term_id: str) -> None:
        super().__init__("GlossaryTerm", term_id)
        self.term_id = term_id


class DuplicateGlossaryTermError(CatalogError):
    """중복 용어 등록 시도"""

    def __init__(self, term_name: str) -> None:
        super().__init__(f"glossary term already exists: {term_name}")
        self.term_name = term_name


class TagNotFoundError(NotFoundError):
    """태그를 찾을 수 없음"""

    def __init__(self, tag_key: str, tag_value: str) -> None:
        super().__init__("Tag", f"{tag_key}:{tag_value}")


class SearchIndexError(CatalogError):
    """검색 인덱스 관련 오류"""

    def __init__(self, message: str) -> None:
        super().__init__(f"search index error: {message}")
