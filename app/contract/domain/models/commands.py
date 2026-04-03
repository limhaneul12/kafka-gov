"""Data Contract Command — 도메인 의도를 표현하는 불변 스키마"""

from __future__ import annotations

from dataclasses import dataclass

from app.contract.domain.models.data_contract import QualityRule, SchemaDefinition
from app.shared.domain.value_objects import SLO, RetentionPolicy
from app.shared.types import CompatibilityMode, ContractId, ProductId


@dataclass(frozen=True, slots=True)
class CreateContractCommand:
    """Data Contract 생성 요청"""

    product_id: ProductId
    name: str
    description: str
    created_by: str


@dataclass(frozen=True, slots=True)
class ProposeVersionCommand:
    """Contract 버전 제안 요청"""

    contract_id: ContractId
    schemas: list[SchemaDefinition]
    quality_rules: list[QualityRule]
    slo: SLO
    compatibility: CompatibilityMode
    retention: RetentionPolicy | None
    changelog: str
    author: str
