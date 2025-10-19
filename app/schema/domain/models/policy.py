"""Schema Policy Models"""

from __future__ import annotations

from dataclasses import dataclass

from .types_enum import DomainCompatibilityMode, SubjectName


@dataclass(frozen=True, slots=True)
class DomainPolicyViolation:
    """정책 위반 정보 - Value Object"""

    subject: SubjectName
    rule: str
    message: str
    severity: str = "error"
    field: str | None = None

    @property
    def is_error(self) -> bool:
        return self.severity == "error"


@dataclass(frozen=True, slots=True)
class DomainSchemaCompatibilityIssue:
    """호환성 위반 상세 - Value Object"""

    path: str
    message: str
    issue_type: str


@dataclass(frozen=True, slots=True)
class DomainSchemaCompatibilityReport:
    """호환성 검증 결과 - Value Object"""

    subject: SubjectName
    mode: DomainCompatibilityMode
    is_compatible: bool
    issues: tuple[DomainSchemaCompatibilityIssue, ...] = ()


@dataclass(frozen=True, slots=True)
class DomainSchemaImpactRecord:
    """스키마 영향도 정보 - Value Object"""

    subject: SubjectName
    topics: tuple[str, ...] = ()
    consumers: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class DomainSchemaDeleteImpact:
    """스키마 삭제 영향도 분석 결과 - Value Object"""

    subject: SubjectName
    current_version: int | None
    total_versions: int
    affected_topics: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    safe_to_delete: bool = False
