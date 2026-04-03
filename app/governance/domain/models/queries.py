"""거버넌스 Query/Result — 조회 요청과 응답 불변 스키마"""

from __future__ import annotations

from dataclasses import dataclass

from app.governance.domain.models.governance import PolicyEvaluation


@dataclass(frozen=True, slots=True)
class EvaluationSummary:
    """정책 평가 결과 요약"""

    evaluations: list[PolicyEvaluation]
    total_violations: int
    has_critical: bool
    overall_score: float
    requires_approval: bool
