"""Data Contract 도메인 모델 — 데이터 생산자와 소비자 간의 계약

Data Contract는 Data Product가 외부에 노출하는 인터페이스의 명세다.
스키마 구조, SLO, 품질 규칙, 호환성 정책을 하나의 계약으로 묶는다.

Schema Registry의 Subject는 Data Contract의 *구현 수단*이다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.contract.types import ContractRole, ContractStatus
from app.shared.domain.value_objects import (
    SLO,
    CompatibilityMode,
    ContractId,
    ProductId,
    QualityDimension,
    QualityThreshold,
    RetentionPolicy,
    SchemaFormat,
)
from app.shared.exceptions.contract_exceptions import (
    ContractRetiredError,
    ContractVersionNotFoundError,
    InvalidContractTransitionError,
)


@dataclass(frozen=True, slots=True)
class SchemaDefinition:
    """스키마 정의 — Contract에 포함되는 스키마 명세"""

    role: ContractRole
    format: SchemaFormat
    schema_body: str
    subject: str | None = None
    version: int | None = None
    schema_id: int | None = None

    @property
    def is_registered(self) -> bool:
        return self.subject is not None and self.version is not None


@dataclass(frozen=True, slots=True)
class QualityRule:
    """데이터 품질 규칙 — Contract 내 비즈니스 품질 요구사항"""

    rule_id: str
    name: str
    dimension: QualityDimension
    field: str | None
    expression: str
    threshold: QualityThreshold
    is_critical: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "dimension": self.dimension.value,
            "field": self.field,
            "expression": self.expression,
            "threshold": self.threshold.threshold,
            "is_critical": self.is_critical,
        }


@dataclass(frozen=True, slots=True)
class ContractVersion:
    """계약 버전 — 불변 스냅샷"""

    version: int
    schemas: tuple[SchemaDefinition, ...]
    quality_rules: tuple[QualityRule, ...]
    slo: SLO
    compatibility: CompatibilityMode
    retention: RetentionPolicy | None
    changelog: str
    created_by: str
    created_at: datetime


@dataclass(slots=True)
class DataContract:
    """Data Contract — 데이터 생산자-소비자 간 계약

    Data Product에 종속되며, 스키마·SLO·품질 규칙을 하나로 묶는다.
    버전 관리가 되며, 호환성 검증은 Contract 수준에서 수행한다.

    Aggregate Root.
    """

    contract_id: ContractId
    product_id: ProductId
    name: str
    description: str
    status: ContractStatus

    # 현재 활성 버전
    current_version: ContractVersion | None = None

    # 버전 히스토리
    version_history: list[ContractVersion] = field(default_factory=list)

    # 감사
    created_by: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None

    # ------------------------------------------------------------------ #
    # 불변 조건
    # ------------------------------------------------------------------ #

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("Data Contract name must not be empty")
        if not self.product_id:
            raise ValueError("Data Contract must belong to a Data Product")

    # ------------------------------------------------------------------ #
    # 버전 관리
    # ------------------------------------------------------------------ #

    def propose_version(
        self,
        *,
        schemas: list[SchemaDefinition],
        quality_rules: list[QualityRule],
        slo: SLO,
        compatibility: CompatibilityMode,
        retention: RetentionPolicy | None,
        changelog: str,
        author: str,
    ) -> ContractVersion:
        """새 버전을 제안한다. 아직 활성화되지 않은 상태."""
        if self.status is ContractStatus.RETIRED:
            raise ContractRetiredError(self.contract_id)

        next_version_num = (
            max(v.version for v in self.version_history) + 1 if self.version_history else 1
        )

        version = ContractVersion(
            version=next_version_num,
            schemas=tuple(schemas),
            quality_rules=tuple(quality_rules),
            slo=slo,
            compatibility=compatibility,
            retention=retention,
            changelog=changelog,
            created_by=author,
            created_at=datetime.now(),
        )

        self.version_history.append(version)
        self.status = ContractStatus.PROPOSED
        return version

    def activate_version(self, version_num: int) -> None:
        """제안된 버전을 활성화한다."""
        version = self._find_version(version_num)
        self.current_version = version
        self.status = ContractStatus.ACTIVE

    def deprecate(self, reason: str) -> None:
        if self.status not in (ContractStatus.ACTIVE, ContractStatus.BREAKING_CHANGE):
            raise InvalidContractTransitionError(self.status.value, ContractStatus.DEPRECATED.value)
        self.status = ContractStatus.DEPRECATED

    def retire(self) -> None:
        if self.status is not ContractStatus.DEPRECATED:
            raise InvalidContractTransitionError(self.status.value, ContractStatus.RETIRED.value)
        self.status = ContractStatus.RETIRED

    # ------------------------------------------------------------------ #
    # 호환성 검증
    # ------------------------------------------------------------------ #

    def check_breaking_change(self, proposed: ContractVersion) -> list[str]:
        """현재 활성 버전 대비 호환성 위반 사항을 반환한다.

        실제 스키마 호환성 검증은 인프라 어댑터(Schema Registry)에 위임하지만,
        Contract 수준에서의 계약 위반(SLO 하향, 품질 규칙 삭제 등)은 여기서 검사한다.
        """
        if self.current_version is None:
            return []

        violations: list[str] = []
        current = self.current_version

        # SLO 하향 검사
        if proposed.slo.availability_percent < current.slo.availability_percent:
            violations.append(
                f"SLO availability degraded: "
                f"{current.slo.availability_percent}% → {proposed.slo.availability_percent}%"
            )

        if proposed.slo.freshness_seconds > current.slo.freshness_seconds:
            violations.append(
                f"SLO freshness degraded: "
                f"{current.slo.freshness_seconds}s → {proposed.slo.freshness_seconds}s"
            )

        # 필수 품질 규칙 삭제 검사
        current_critical_ids = {r.rule_id for r in current.quality_rules if r.is_critical}
        proposed_rule_ids = {r.rule_id for r in proposed.quality_rules}
        removed_critical = current_critical_ids - proposed_rule_ids
        if removed_critical:
            violations.append(
                f"critical quality rules removed: {', '.join(sorted(removed_critical))}"
            )

        # 호환성 모드 완화 검사
        strict_order = [
            CompatibilityMode.FULL_TRANSITIVE,
            CompatibilityMode.FULL,
            CompatibilityMode.BACKWARD_TRANSITIVE,
            CompatibilityMode.BACKWARD,
            CompatibilityMode.FORWARD_TRANSITIVE,
            CompatibilityMode.FORWARD,
            CompatibilityMode.NONE,
        ]
        current_idx = (
            strict_order.index(current.compatibility)
            if current.compatibility in strict_order
            else len(strict_order)
        )
        proposed_idx = (
            strict_order.index(proposed.compatibility)
            if proposed.compatibility in strict_order
            else len(strict_order)
        )
        if proposed_idx > current_idx:
            violations.append(
                f"compatibility mode relaxed: "
                f"{current.compatibility.value} → {proposed.compatibility.value}"
            )

        return violations

    # ------------------------------------------------------------------ #
    # 쿼리
    # ------------------------------------------------------------------ #

    @property
    def latest_version_num(self) -> int:
        if not self.version_history:
            return 0
        return max(v.version for v in self.version_history)

    @property
    def schemas(self) -> tuple[SchemaDefinition, ...]:
        if self.current_version is None:
            return ()
        return self.current_version.schemas

    @property
    def quality_rules(self) -> tuple[QualityRule, ...]:
        if self.current_version is None:
            return ()
        return self.current_version.quality_rules

    # ------------------------------------------------------------------ #
    # 내부 헬퍼
    # ------------------------------------------------------------------ #

    def _find_version(self, version_num: int) -> ContractVersion:
        for v in self.version_history:
            if v.version == version_num:
                return v
        raise ContractVersionNotFoundError(self.contract_id, version_num)
