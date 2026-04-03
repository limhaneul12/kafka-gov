"""Data Product Query/Result — 조회 요청과 응답 불변 스키마"""

from __future__ import annotations

from dataclasses import dataclass

from app.product.domain.models.data_product import DataProduct
from app.shared.types import DomainName, Environment, Lifecycle


@dataclass(frozen=True, slots=True)
class ListProductsQuery:
    """Data Product 목록 조회 요청"""

    domain: DomainName | None = None
    environment: Environment | None = None
    lifecycle: Lifecycle | None = None
    limit: int = 50
    offset: int = 0


@dataclass(frozen=True, slots=True)
class ListProductsResult:
    """Data Product 목록 조회 응답"""

    items: list[DataProduct]
    total: int
    limit: int
    offset: int
