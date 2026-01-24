"""Schema Lint Service - Advisory Only"""

from __future__ import annotations

import orjson

from app.schema.domain.models.lint import LintReport, LintViolation, ViolationSeverity
from app.schema.domain.policies.base import ISchemaLintPolicy
from app.schema.domain.policies.naming import FieldNamingPolicy
from app.schema.domain.policies.security import PiiCandidatePolicy
from app.schema.domain.policies.structure import (
    BytesOverusePolicy,
    DeepMapPolicy,
    ExcessiveUnionPolicy,
)


class SchemaLintService:
    """Schema Lint Service - 도메인 정책을 조합하여 실행

    책임:
    - JSON 파싱 및 에러 핸들링
    - 등록된 정책들의 실행 및 결과 취합
    - 최종 점수(Score) 계산
    """

    def __init__(self) -> None:
        # 정책 등록 (Composition)
        self.policies: list[ISchemaLintPolicy] = [
            FieldNamingPolicy(),
            PiiCandidatePolicy(),
            BytesOverusePolicy(),
            ExcessiveUnionPolicy(),
            DeepMapPolicy(),
        ]

    def lint_avro_schema(self, schema_str: str) -> LintReport:
        """Avro 스키마 린트 검사

        Args:
            schema_str: Avro 스키마 JSON 문자열

        Returns:
            LintReport: 린트 결과 (위반 사항 및 점수)
        """
        violations: list[LintViolation] = []

        try:
            schema_dict = orjson.loads(schema_str)

            # 모든 정책 실행
            for policy in self.policies:
                violations.extend(policy.check(schema_dict))

            # 점수 계산 위임
            pii_score = self._calculate_pii_score(schema_dict, violations)
            risk_score = self._calculate_risk_score(violations)

        except Exception as e:
            # 파싱 실패 처리
            violations.append(
                LintViolation(
                    code="PARSE_ERROR",
                    severity=ViolationSeverity.WARN,
                    rule="스키마 파싱 가능",
                    actual=f"Parse failed: {e}",
                    hint="유효한 JSON/Avro 스키마인지 확인하세요",
                )
            )
            pii_score = 0.0
            risk_score = 0.5

        return LintReport(
            violations=violations,
            pii_score=pii_score,
            risk_score=risk_score,
        )

    def _calculate_pii_score(self, schema_dict: dict, violations: list[LintViolation]) -> float:
        """PII 점수 계산 로직"""
        # PII 관련 위반 개수 확인
        pii_violation_count = sum(1 for v in violations if v.code == "PII_CANDIDATE")
        total_fields = len(schema_dict.get("fields", []))

        # 0으로 나누기 방지
        if total_fields == 0:
            return 0.0

        scene_score = pii_violation_count / total_fields
        return min(scene_score, 1.0)

    def _calculate_risk_score(self, violations: list[LintViolation]) -> float:
        """리스크 점수 계산 로직"""
        score = sum(0.3 if v.severity == ViolationSeverity.WARN else 0.1 for v in violations)
        return min(score, 1.0)
