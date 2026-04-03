"""Data Product 생명주기 관리 유스케이스 — activate, deprecate, retire"""

from __future__ import annotations

import logging
from datetime import datetime

from app.product.domain.models.data_product import DataProduct
from app.product.domain.repositories.product_repository import IDataProductRepository
from app.shared.exceptions.product_exceptions import DataProductNotFoundError
from app.shared.types import ProductId

logger = logging.getLogger(__name__)


class ActivateProductUseCase:
    """Data Product 활성화 (INCUBATION → ACTIVE)

    전제조건: infra binding이 최소 1개 이상 존재해야 한다.
    """

    def __init__(self, repository: IDataProductRepository) -> None:
        self._repository = repository

    async def execute(self, product_id: ProductId) -> DataProduct:
        product = await self._load(product_id)
        product.activate()
        product.updated_at = datetime.now()
        await self._repository.save(product)

        logger.info(
            "data_product_activated",
            extra={"product_id": product_id},
        )
        return product

    async def _load(self, product_id: ProductId) -> DataProduct:
        product = await self._repository.find_by_id(product_id)
        if product is None:
            raise DataProductNotFoundError(product_id)
        return product


class DeprecateProductUseCase:
    """Data Product 비활성화 (ACTIVE → DEPRECATED)"""

    def __init__(self, repository: IDataProductRepository) -> None:
        self._repository = repository

    async def execute(self, product_id: ProductId, reason: str) -> DataProduct:
        product = await self._load(product_id)
        product.deprecate(reason)
        product.updated_at = datetime.now()
        await self._repository.save(product)

        logger.info(
            "data_product_deprecated",
            extra={"product_id": product_id, "reason": reason},
        )
        return product

    async def _load(self, product_id: ProductId) -> DataProduct:
        product = await self._repository.find_by_id(product_id)
        if product is None:
            raise DataProductNotFoundError(product_id)
        return product


class RetireProductUseCase:
    """Data Product 폐기 (DEPRECATED → RETIRED)

    전제조건: 활성 소비자가 0명이어야 한다.
    """

    def __init__(self, repository: IDataProductRepository) -> None:
        self._repository = repository

    async def execute(self, product_id: ProductId) -> DataProduct:
        product = await self._load(product_id)
        product.retire()
        product.updated_at = datetime.now()
        await self._repository.save(product)

        logger.info(
            "data_product_retired",
            extra={"product_id": product_id},
        )
        return product

    async def _load(self, product_id: ProductId) -> DataProduct:
        product = await self._repository.find_by_id(product_id)
        if product is None:
            raise DataProductNotFoundError(product_id)
        return product
