"""Data Product 생성 유스케이스"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime

from app.product.domain.models.commands import CreateProductCommand
from app.product.domain.models.data_product import DataProduct
from app.product.domain.repositories.product_repository import IDataProductRepository
from app.shared.domain.value_objects import Tag, TeamOwnership
from app.shared.exceptions.base_exceptions import ConflictError
from app.shared.types import Lifecycle, ProductId

logger = logging.getLogger(__name__)


class CreateProductUseCase:
    """Data Product 생성

    비즈니스 규칙:
    - 이름 중복 불허
    - 생성 시 lifecycle은 항상 INCUBATION
    - 생성 후 infra binding을 추가해야 activate 가능
    """

    def __init__(self, repository: IDataProductRepository) -> None:
        self._repository = repository

    async def execute(self, command: CreateProductCommand) -> DataProduct:
        existing = await self._repository.find_by_name(command.name)
        if existing is not None:
            raise ConflictError("DataProduct", command.name)

        product = DataProduct(
            product_id=_generate_id(),
            name=command.name,
            description=command.description,
            domain=command.domain,
            owner=TeamOwnership(
                team_id=command.owner_team_id,
                team_name=command.owner_team_name,
                domain=command.owner_domain,
                contact_channel=command.contact_channel,
            ),
            classification=command.classification,
            environment=command.environment,
            lifecycle=Lifecycle.INCUBATION,
            tags=[Tag(key=k, value=v) for k, v in (command.tags or [])],
            created_by=command.created_by,
            created_at=datetime.now(),
        )

        await self._repository.save(product)

        logger.info(
            "data_product_created",
            extra={
                "product_id": product.product_id,
                "name": product.name,
                "domain": product.domain,
                "created_by": command.created_by,
            },
        )

        return product


def _generate_id() -> ProductId:
    return f"dp-{uuid.uuid4().hex[:12]}"
