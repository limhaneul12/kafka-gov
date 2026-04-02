"""Data Contract 도메인 예외"""

from __future__ import annotations

from app.shared.domain.value_objects import ContractId
from app.shared.exceptions.base_exceptions import DomainError, NotFoundError


class DataContractError(DomainError):
    """Data Contract 도메인 예외 베이스"""


class ContractRetiredError(DataContractError):
    """이미 폐기된 계약에 대한 조작 시도"""

    def __init__(self, contract_id: ContractId) -> None:
        super().__init__(f"contract is retired: {contract_id}")
        self.contract_id = contract_id


class ContractVersionNotFoundError(NotFoundError):
    """계약 버전을 찾을 수 없음"""

    def __init__(self, contract_id: ContractId, version: int) -> None:
        super().__init__("ContractVersion", f"{contract_id}@v{version}")
        self.contract_id = contract_id
        self.version = version


class InvalidContractTransitionError(DataContractError):
    """허용되지 않는 계약 상태 전이"""

    def __init__(self, current: str, target: str) -> None:
        super().__init__(f"invalid contract transition: {current} → {target}")
        self.current = current
        self.target = target


class DataContractNotFoundError(NotFoundError):
    """Data Contract를 찾을 수 없음"""

    def __init__(self, contract_id: ContractId) -> None:
        super().__init__("DataContract", contract_id)
        self.contract_id = contract_id


class BreakingChangeError(DataContractError):
    """호환성 위반 변경 감지"""

    def __init__(self, violations: list[str]) -> None:
        summary = "; ".join(violations[:3])
        super().__init__(f"breaking change detected: {summary}")
        self.violations = violations
