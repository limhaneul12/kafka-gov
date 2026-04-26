"""Governance Domain Models"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True, slots=True, kw_only=True)
class GovernanceScore:
    """거버넌스 점수 도메인 모델"""

    compatibility_pass_rate: float
    documentation_coverage: float
    average_lint_score: float
    total_score: float


@dataclass(frozen=True, slots=True, kw_only=True)
class SubjectStat:
    """Subject 별 거버넌스 통계 도메인 모델"""

    subject: str
    owner: str | None = None
    version_count: int = 0
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())
    compatibility_mode: str | None = None
    lint_score: float = 0.0
    has_doc: bool = False
    violations: list[Any] = field(default_factory=list)


@dataclass(frozen=True, slots=True, kw_only=True)
class GovernanceDashboardStats:
    """거버넌스 대시보드 통계 도메인 모델"""

    total_subjects: int
    total_versions: int
    orphan_subjects: int
    scores: GovernanceScore
    top_subjects: list[SubjectStat]


@dataclass(frozen=True, slots=True, kw_only=True)
class SubjectDetail:
    """스키마 상세 정보 도메인 모델"""

    subject: str
    version: int
    schema_id: int
    schema_str: str
    schema_type: str
    compatibility_mode: str
    owner: str | None = None
    doc: str | None = None
    tags: list[str] = field(default_factory=list)
    description: str | None = None
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    violations: list[Any] = field(default_factory=list)
    policy_score: float = 1.0


@dataclass(frozen=True, slots=True, kw_only=True)
class SchemaHistoryItem:
    """스키마 변경 이력 도메인 모델"""

    version: int
    schema_id: int
    diff_type: str
    created_at: str | None = None
    author: str | None = None
    commit_message: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class SubjectHistory:
    """Subject 전체 이력 도메인 모델"""

    subject: str
    history: list[SchemaHistoryItem]


@dataclass(frozen=True, slots=True, kw_only=True)
class SubjectVersionSummary:
    """Subject 버전 목록 항목"""

    version: int
    schema_id: int
    schema_type: str
    hash: str
    canonical_hash: str | None = None
    created_at: str | None = None
    author: str | None = None
    commit_message: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class SubjectVersionList:
    """Subject 버전 목록"""

    subject: str
    versions: list[SubjectVersionSummary]


@dataclass(frozen=True, slots=True, kw_only=True)
class SubjectVersionDetail:
    """특정 버전 스키마 상세"""

    subject: str
    version: int
    schema_id: int
    schema_str: str
    schema_type: str
    hash: str
    canonical_hash: str | None = None
    references: list[dict[str, str | int]] = field(default_factory=list)
    owner: str | None = None
    compatibility_mode: str | None = None
    created_at: str | None = None
    author: str | None = None
    commit_message: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class SubjectVersionComparison:
    """두 스키마 버전 비교 결과"""

    subject: str
    from_version: int
    to_version: int
    changed: bool
    diff_type: str
    changes: list[str]
    schema_type: str
    compatibility_mode: str | None = None
    from_schema: str | None = None
    to_schema: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class SubjectDriftReport:
    """Registry latest 상태와 로컬 catalog snapshot 간 drift 보고서"""

    subject: str
    registry_latest_version: int
    registry_canonical_hash: str | None = None
    catalog_latest_version: int | None = None
    catalog_canonical_hash: str | None = None
    observed_version: int | None = None
    last_synced_at: str | None = None
    drift_flags: list[str] = field(default_factory=list)
    has_drift: bool = False


@dataclass(frozen=True, slots=True, kw_only=True)
class SchemaVersionExport:
    """스키마 버전 export 정보"""

    subject: str
    version: int
    schema_type: str
    filename: str
    media_type: str
    schema_str: str
