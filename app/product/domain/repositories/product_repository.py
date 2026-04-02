"""Data Product 리포지토리 포트 — 도메인이 인프라에 요구하는 인터페이스"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.product.domain.models.data_product import DataProduct
from app.shared.types import DomainName, Environment, Lifecycle, ProductId


class IDataProductRepository(ABC):
    """Data Product 영속성 포트"""

    @abstractmethod
    async def save(self, product: DataProduct) -> None:
        """Data Product를 저장(생성 또는 갱신)한다."""

    @abstractmethod
    async def find_by_id(self, product_id: ProductId) -> DataProduct | None:
        """ID로 Data Product를 조회한다."""

    @abstractmethod
    async def find_by_name(self, name: str) -> DataProduct | None:
        """이름으로 Data Product를 조회한다."""

    @abstractmethod
    async def list_by_domain(
        self,
        domain: DomainName,
        *,
        lifecycle: Lifecycle | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[DataProduct]:
        """도메인별 Data Product 목록을 조회한다."""

    @abstractmethod
    async def list_by_environment(
        self,
        environment: Environment,
        *,
        lifecycle: Lifecycle | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[DataProduct]:
        """환경별 Data Product 목록을 조회한다."""

    @abstractmethod
    async def list_all(
        self,
        *,
        lifecycle: Lifecycle | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[DataProduct]:
        """전체 Data Product 목록을 조회한다."""

    @abstractmethod
    async def count(self, *, lifecycle: Lifecycle | None = None) -> int:
        """Data Product 수를 반환한다."""

    @abstractmethod
    async def delete(self, product_id: ProductId) -> None:
        """Data Product를 삭제한다."""
