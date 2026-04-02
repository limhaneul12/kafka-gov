"""Data Contract 생성 유스케이스"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime

from app.contract.domain.models.commands import CreateContractCommand
from app.contract.domain.models.data_contract import DataContract
from app.contract.domain.repositories.contract_repository import IDataContractRepository
from app.contract.types import ContractStatus
from app.product.domain.repositories.product_repository import IDataProductRepository
from app.shared.exceptions.base_exceptions import ConflictError
from app.shared.exceptions.product_exceptions import DataProductNotFoundError
from app.shared.types import ContractId

logger = logging.getLogger(__name__)


class CreateContractUseCase:
    """Data Contract 생성

    비즈니스 규칙:
    - 소속 Data Product가 존재해야 한다
    - 같은 Product 내 동일 이름 Contract 불허
    - 생성 시 status는 항상 DRAFT
    """

    def __init__(
        self,
        contract_repository: IDataContractRepository,
        product_repository: IDataProductRepository,
    ) -> None:
        self._contract_repo = contract_repository
        self._product_repo = product_repository

    async def execute(self, command: CreateContractCommand) -> DataContract:
        product = await self._product_repo.find_by_id(command.product_id)
        if product is None:
            raise DataProductNotFoundError(command.product_id)

        existing_contracts = await self._contract_repo.list_by_product(command.product_id)
        for c in existing_contracts:
            if c.name == command.name:
                raise ConflictError("DataContract", command.name)

        contract = DataContract(
            contract_id=_generate_id(),
            product_id=command.product_id,
            name=command.name,
            description=command.description,
            status=ContractStatus.DRAFT,
            created_by=command.created_by,
            created_at=datetime.now(),
        )

        await self._contract_repo.save(contract)

        logger.info(
            "data_contract_created",
            extra={
                "contract_id": contract.contract_id,
                "product_id": command.product_id,
                "name": command.name,
            },
        )
        return contract


def _generate_id() -> ContractId:
    return f"dc-{uuid.uuid4().hex[:12]}"
