"""Data Contract 버전 제안 유스케이스"""

from __future__ import annotations

import logging

from app.contract.domain.models.commands import ProposeVersionCommand
from app.contract.domain.models.data_contract import ContractVersion, DataContract
from app.contract.domain.repositories.contract_repository import IDataContractRepository
from app.shared.exceptions.contract_exceptions import DataContractNotFoundError

logger = logging.getLogger(__name__)


class ProposeVersionUseCase:
    """Data Contract에 새 버전을 제안

    비즈니스 규칙:
    - RETIRED 상태의 Contract에는 제안 불가
    - 기존 활성 버전 대비 breaking change 검사 수행
    - breaking change가 있으면 Contract 상태를 BREAKING_CHANGE로 전환
    """

    def __init__(self, repository: IDataContractRepository) -> None:
        self._repository = repository

    async def execute(
        self, command: ProposeVersionCommand
    ) -> tuple[DataContract, ContractVersion, list[str]]:
        """Returns: (contract, new_version, breaking_violations)"""
        contract = await self._repository.find_by_id(command.contract_id)
        if contract is None:
            raise DataContractNotFoundError(command.contract_id)

        version = contract.propose_version(
            schemas=command.schemas,
            quality_rules=command.quality_rules,
            slo=command.slo,
            compatibility=command.compatibility,
            retention=command.retention,
            changelog=command.changelog,
            author=command.author,
        )

        violations = contract.check_breaking_change(version)

        await self._repository.save(contract)

        logger.info(
            "contract_version_proposed",
            extra={
                "contract_id": command.contract_id,
                "version": version.version,
                "breaking_violations": len(violations),
            },
        )

        return contract, version, violations
