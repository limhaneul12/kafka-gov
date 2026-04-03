"""Data Product Command — 도메인 의도를 표현하는 불변 스키마"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.shared.types import (
    DataClassification,
    DomainName,
    Environment,
    InfraType,
    ProductId,
)


@dataclass(frozen=True, slots=True)
class CreateProductCommand:
    """Data Product 생성 요청"""

    name: str
    description: str
    domain: DomainName
    owner_team_id: str
    owner_team_name: str
    owner_domain: DomainName
    classification: DataClassification
    environment: Environment
    created_by: str
    contact_channel: str | None = None
    tags: list[tuple[str, str]] | None = None


@dataclass(frozen=True, slots=True)
class BindInfraCommand:
    """인프라 바인딩 요청"""

    product_id: ProductId
    infra_type: InfraType
    resource_id: str
    cluster_id: str | None = None
    config: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class UnbindInfraCommand:
    """인프라 바인딩 해제 요청"""

    product_id: ProductId
    infra_type: InfraType
    resource_id: str
