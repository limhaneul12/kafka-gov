"""Data Contract 리포지토리 포트 — 도메인이 인프라에 요구하는 인터페이스"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.contract.domain.models.data_contract import DataContract
from app.contract.types import ContractStatus
from app.shared.types import ContractId, ProductId


class IDataContractRepository(ABC):
    """Data Contract 영속성 포트"""

    @abstractmethod
    async def save(self, contract: DataContract) -> None:
        """Data Contract를 저장(생성 또는 갱신)한다."""

    @abstractmethod
    async def find_by_id(self, contract_id: ContractId) -> DataContract | None:
        """ID로 Data Contract를 조회한다."""

    @abstractmethod
    async def list_by_product(
        self,
        product_id: ProductId,
        *,
        status: ContractStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[DataContract]:
        """Data Product에 속한 Contract 목록을 조회한다."""

    @abstractmethod
    async def list_active(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[DataContract]:
        """활성 상태 Contract 목록을 조회한다."""

    @abstractmethod
    async def count_by_product(self, product_id: ProductId) -> int:
        """Data Product에 속한 Contract 수를 반환한다."""

    @abstractmethod
    async def delete(self, contract_id: ContractId) -> None:
        """Data Contract를 삭제한다."""
