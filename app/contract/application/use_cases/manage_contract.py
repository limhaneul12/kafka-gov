"""Data Contract 생명주기 관리 유스케이스 — activate, deprecate, retire"""

from __future__ import annotations

import logging
from datetime import datetime

from app.contract.domain.models.data_contract import DataContract
from app.contract.domain.repositories.contract_repository import IDataContractRepository
from app.shared.exceptions.contract_exceptions import DataContractNotFoundError
from app.shared.types import ContractId

logger = logging.getLogger(__name__)


class ActivateVersionUseCase:
    """제안된 Contract 버전을 활성화"""

    def __init__(self, repository: IDataContractRepository) -> None:
        self._repository = repository

    async def execute(self, contract_id: ContractId, version_num: int) -> DataContract:
        contract = await self._load(contract_id)
        contract.activate_version(version_num)
        contract.updated_at = datetime.now()
        await self._repository.save(contract)

        logger.info(
            "contract_version_activated",
            extra={"contract_id": contract_id, "version": version_num},
        )
        return contract

    async def _load(self, contract_id: ContractId) -> DataContract:
        contract = await self._repository.find_by_id(contract_id)
        if contract is None:
            raise DataContractNotFoundError(contract_id)
        return contract


class DeprecateContractUseCase:
    """Data Contract 비활성화"""

    def __init__(self, repository: IDataContractRepository) -> None:
        self._repository = repository

    async def execute(self, contract_id: ContractId, reason: str) -> DataContract:
        contract = await self._load(contract_id)
        contract.deprecate(reason)
        contract.updated_at = datetime.now()
        await self._repository.save(contract)

        logger.info(
            "contract_deprecated",
            extra={"contract_id": contract_id, "reason": reason},
        )
        return contract

    async def _load(self, contract_id: ContractId) -> DataContract:
        contract = await self._repository.find_by_id(contract_id)
        if contract is None:
            raise DataContractNotFoundError(contract_id)
        return contract


class RetireContractUseCase:
    """Data Contract 폐기"""

    def __init__(self, repository: IDataContractRepository) -> None:
        self._repository = repository

    async def execute(self, contract_id: ContractId) -> DataContract:
        contract = await self._load(contract_id)
        contract.retire()
        contract.updated_at = datetime.now()
        await self._repository.save(contract)

        logger.info(
            "contract_retired",
            extra={"contract_id": contract_id},
        )
        return contract

    async def _load(self, contract_id: ContractId) -> DataContract:
        contract = await self._repository.find_by_id(contract_id)
        if contract is None:
            raise DataContractNotFoundError(contract_id)
        return contract
