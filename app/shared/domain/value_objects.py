"""공통 도메인 값 객체 — Value Object dataclass만 정의

TypeAlias와 StrEnum은 app.shared.types에서 관리한다.
이 파일은 비즈니스 의미를 가진 불변 값 객체만 담는다.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.shared.types import (
    CompatibilityMode,
    ContractId,
    DataClassification,
    DomainName,
    Environment,
    InfraType,
    Lifecycle,
    LineageDirection,
    ProductId,
    QualityDimension,
    SchemaFormat,
    TagValue,
    TeamId,
)

# re-export: 기존 import 경로 호환성 유지
__all__ = [
    "CompatibilityMode",
    "ContractId",
    "DataClassification",
    "DomainName",
    "Environment",
    "InfraType",
    "Lifecycle",
    "LineageDirection",
    "ProductId",
    "QualityDimension",
    "RetentionPolicy",
    "SchemaFormat",
    "SLO",
    "Tag",
    "TagValue",
    "TeamId",
    "TeamOwnership",
    "QualityThreshold",
]


# ============================================================================
# Value Objects
# ============================================================================


@dataclass(frozen=True, slots=True)
class TeamOwnership:
    """데이터 제품 소유권 — 비즈니스 책임의 단위"""

    team_id: TeamId
    team_name: str
    domain: DomainName
    contact_channel: str | None = None

    def __str__(self) -> str:
        return f"{self.team_name} ({self.domain})"


@dataclass(frozen=True, slots=True)
class QualityThreshold:
    """데이터 품질 규칙의 임계값"""

    dimension: QualityDimension
    field: str | None
    operator: str
    threshold: float
    description: str

    def evaluate(self, actual: float) -> bool:
        ops = {
            ">=": lambda a, t: a >= t,
            "<=": lambda a, t: a <= t,
            ">": lambda a, t: a > t,
            "<": lambda a, t: a < t,
            "==": lambda a, t: a == t,
        }
        op_fn = ops.get(self.operator)
        if op_fn is None:
            raise ValueError(f"unsupported operator: {self.operator}")
        return op_fn(actual, self.threshold)


@dataclass(frozen=True, slots=True)
class SLO:
    """서비스 수준 목표 — Data Contract의 비기능 요구사항"""

    availability_percent: float
    freshness_seconds: int
    latency_p99_ms: int | None = None
    throughput_msg_per_sec: int | None = None

    def __post_init__(self) -> None:
        if not 0.0 <= self.availability_percent <= 100.0:
            raise ValueError("availability_percent must be between 0 and 100")
        if self.freshness_seconds < 0:
            raise ValueError("freshness_seconds must be non-negative")


@dataclass(frozen=True, slots=True)
class RetentionPolicy:
    """데이터 보존 정책 — 분류 등급에 따른 보존 규칙"""

    retention_days: int
    classification: DataClassification
    requires_encryption: bool = False
    requires_access_log: bool = False

    def __post_init__(self) -> None:
        if self.retention_days < 1:
            raise ValueError("retention_days must be at least 1")
        if self.classification >= DataClassification.CONFIDENTIAL:
            object.__setattr__(self, "requires_encryption", True)
            object.__setattr__(self, "requires_access_log", True)


@dataclass(frozen=True, slots=True)
class Tag:
    """자유형 태그 — 카탈로그 검색과 분류에 사용"""

    key: str
    value: TagValue

    def __str__(self) -> str:
        return f"{self.key}:{self.value}"
