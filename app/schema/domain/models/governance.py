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
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())


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
class GraphNode:
    """영향도 그래프 노드 도메인 모델"""

    id: str
    type: str
    label: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True, kw_only=True)
class GraphLink:
    """영향도 그래프 링크 도메인 모델"""

    source: str
    target: str
    relation: str


@dataclass(frozen=True, slots=True, kw_only=True)
class ImpactGraph:
    """영향도 그래프 도메인 모델"""

    subject: str
    nodes: list[GraphNode]
    links: list[GraphLink]
