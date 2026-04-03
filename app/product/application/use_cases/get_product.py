"""Data Product 조회 유스케이스"""

from __future__ import annotations

import logging

from app.product.domain.models.data_product import DataProduct
from app.product.domain.repositories.product_repository import IDataProductRepository
from app.shared.exceptions.product_exceptions import DataProductNotFoundError
from app.shared.types import ProductId

logger = logging.getLogger(__name__)


class GetProductUseCase:
    """단일 Data Product 조회"""

    def __init__(self, repository: IDataProductRepository) -> None:
        self._repository = repository

    async def execute(self, product_id: ProductId) -> DataProduct:
        product = await self._repository.find_by_id(product_id)
        if product is None:
            raise DataProductNotFoundError(product_id)
        return product
