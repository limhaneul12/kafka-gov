"""Schema Lint Models"""

from dataclasses import dataclass
from enum import StrEnum


class ViolationSeverity(StrEnum):
    """Lint 위반 심각도"""

    INFO = "INFO"
    WARN = "WARN"


@dataclass(frozen=True, slots=True)
class LintViolation:
    """Lint 위반 항목 - Value Object"""

    code: str  # NAMING_INCONSISTENT, PII_CANDIDATE, BYTES_OVERUSE 등
    severity: ViolationSeverity
    rule: str  # 규칙 설명
    actual: str  # 실제 발견된 값
    hint: str  # 개선 제안
    doc_url: str | None = None  # 문서 링크 (옵션)


@dataclass(frozen=True, slots=True)
class LintReport:
    """Lint 리포트 - Value Object"""

    violations: list[LintViolation]
    pii_score: float  # PII 가능성 점수 (0.0~1.0)
    risk_score: float  # 종합 리스크 점수 (0.0~1.0)

    @staticmethod
    def empty() -> "LintReport":
        return LintReport(violations=[], pii_score=0.0, risk_score=0.0)
