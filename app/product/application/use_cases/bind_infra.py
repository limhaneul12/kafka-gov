"""Data Product 인프라 바인딩 유스케이스"""

from __future__ import annotations

import logging
from datetime import datetime

from app.product.domain.models.commands import BindInfraCommand, UnbindInfraCommand
from app.product.domain.models.data_product import DataProduct, InfraBinding
from app.product.domain.repositories.product_repository import IDataProductRepository
from app.shared.exceptions.product_exceptions import DataProductNotFoundError

logger = logging.getLogger(__name__)


class BindInfraUseCase:
    """Data Product에 인프라 바인딩 추가

    예: Kafka Topic, Schema Registry Subject, S3 Bucket 등을 연결
    """

    def __init__(self, repository: IDataProductRepository) -> None:
        self._repository = repository

    async def execute(self, command: BindInfraCommand) -> DataProduct:
        product = await self._repository.find_by_id(command.product_id)
        if product is None:
            raise DataProductNotFoundError(command.product_id)

        binding = InfraBinding(
            infra_type=command.infra_type,
            resource_id=command.resource_id,
            cluster_id=command.cluster_id,
            config=command.config,
        )

        product.bind_infra(binding)
        product.updated_at = datetime.now()
        await self._repository.save(product)

        logger.info(
            "infra_binding_added",
            extra={
                "product_id": command.product_id,
                "infra_type": command.infra_type,
                "resource_id": command.resource_id,
            },
        )
        return product


class UnbindInfraUseCase:
    """Data Product에서 인프라 바인딩 제거"""

    def __init__(self, repository: IDataProductRepository) -> None:
        self._repository = repository

    async def execute(self, command: UnbindInfraCommand) -> DataProduct:
        product = await self._repository.find_by_id(command.product_id)
        if product is None:
            raise DataProductNotFoundError(command.product_id)

        product.unbind_infra(command.infra_type, command.resource_id)
        product.updated_at = datetime.now()
        await self._repository.save(product)

        logger.info(
            "infra_binding_removed",
            extra={
                "product_id": command.product_id,
                "infra_type": command.infra_type,
                "resource_id": command.resource_id,
            },
        )
        return product
