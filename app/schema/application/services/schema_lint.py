"""Schema Lint Service - Advisory Only

권고 전용 린트 (차단 금지)
- 필드 네이밍 일관성
- PII 후보 태깅
- bytes 남용, 과도한 union, 깊은 map
- 결과는 lint_report로 저장, 차단하지 않음
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, ClassVar

import orjson


class ViolationSeverity(str, Enum):
    """Lint 위반 심각도"""

    INFO = "INFO"
    WARN = "WARN"


@dataclass
class LintViolation:
    """Lint 위반 항목"""

    code: str  # NAMING_INCONSISTENT, PII_CANDIDATE, BYTES_OVERUSE 등
    severity: ViolationSeverity
    rule: str  # 규칙 설명
    actual: str  # 실제 발견된 값
    hint: str  # 개선 제안
    doc_url: str | None = None  # 문서 링크 (옵션)


@dataclass
class LintReport:
    """Lint 리포트"""

    violations: list[LintViolation]
    pii_score: float  # PII 가능성 점수 (0.0~1.0)
    risk_score: float  # 종합 리스크 점수 (0.0~1.0)


class SchemaLintService:
    """Schema Lint Service - Advisory Mode

    OSS 원칙:
    - 권고만, 차단 없음
    - 점수화로 우선순위 제공
    - 가이드 중심
    """

    # PII 키워드 사전
    PII_KEYWORDS: ClassVar[set[str]] = {
        "email",
        "phone",
        "ssn",
        "social",
        "passport",
        "address",
        "name",
        "birth",
        "card",
        "account",
    }

    def lint_avro_schema(self, schema_str: str) -> LintReport:
        """Avro 스키마 린트 검사

        Args:
            schema_str: Avro 스키마 JSON 문자열

        Returns:
            LintReport: 린트 결과
        """
        violations: list[LintViolation] = []

        try:
            schema_dict = orjson.loads(schema_str)

            # 1. 필드 네이밍 일관성 체크
            violations.extend(self._check_field_naming(schema_dict))

            # 2. PII 후보 태깅
            pii_violations = self._check_pii_candidates(schema_dict)
            violations.extend(pii_violations)
            pii_score = len(pii_violations) / max(len(schema_dict.get("fields", [])), 1)
            pii_score = min(pii_score, 1.0)

            # 3. bytes 타입 남용 체크
            violations.extend(self._check_bytes_overuse(schema_dict))

            # 4. 과도한 union 체크
            violations.extend(self._check_excessive_unions(schema_dict))

            # 5. 깊은 map 체크
            violations.extend(self._check_deep_maps(schema_dict))

            # 리스크 점수 계산 (WARN=0.3, INFO=0.1)
            risk_score = sum(
                0.3 if v.severity == ViolationSeverity.WARN else 0.1 for v in violations
            )
            risk_score = min(risk_score, 1.0)

        except Exception as e:
            # 파싱 실패
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

    def _check_field_naming(self, schema_dict: dict[str, Any]) -> list[LintViolation]:
        """필드 네이밍 일관성 체크

        snake_case vs camelCase 혼용 감지
        """
        violations: list[LintViolation] = []
        fields = schema_dict.get("fields", [])

        if not fields:
            return violations

        # 네이밍 패턴 분석
        snake_count = 0
        camel_count = 0

        for field in fields:
            name = field.get("name", "")
            if "_" in name:
                snake_count += 1
            elif re.match(r"^[a-z]+[A-Z]", name):
                camel_count += 1

        # 혼용 감지
        if snake_count > 0 and camel_count > 0:
            violations.append(
                LintViolation(
                    code="NAMING_INCONSISTENT",
                    severity=ViolationSeverity.WARN,
                    rule="필드명은 snake_case 또는 camelCase 중 하나로 통일",
                    actual=f"snake_case: {snake_count}, camelCase: {camel_count}",
                    hint="Avro는 snake_case 권장 (Kafka 관례)",
                )
            )

        return violations

    def _check_pii_candidates(self, schema_dict: dict[str, Any]) -> list[LintViolation]:
        """PII 후보 필드 태깅"""
        fields = schema_dict.get("fields", [])
        violations: list[LintViolation] = []

        for field in fields:
            # PII 키워드 매칭
            matched_keywords = [
                kw for kw in self.PII_KEYWORDS if kw in field.get("name", "").lower()
            ]

            if matched_keywords:
                violations.append(
                    LintViolation(
                        code="PII_CANDIDATE",
                        severity=ViolationSeverity.INFO,
                        rule="PII 가능성이 있는 필드명",
                        actual=f"필드: {field.get('name')}, 키워드: {matched_keywords}",
                        hint="민감 데이터라면 암호화/마스킹 고려",
                        doc_url="https://kafka-gov.example.com/docs/pii-handling",
                    )
                )

        return violations

    def _check_bytes_overuse(self, schema_dict: dict[str, Any]) -> list[LintViolation]:
        """bytes 타입 남용 체크

        bytes는 바이너리 데이터 전용. 문자열은 string 사용 권장
        """
        violations: list[LintViolation] = []
        fields = schema_dict.get("fields", [])

        bytes_count = sum(1 for f in fields if f.get("type") == "bytes")

        if bytes_count > 3:  # 임계값: 3개 이상
            violations.append(
                LintViolation(
                    code="BYTES_OVERUSE",
                    severity=ViolationSeverity.WARN,
                    rule="bytes 타입은 바이너리 전용, 문자열은 string 사용",
                    actual=f"{bytes_count}개 bytes 필드 발견",
                    hint="base64 인코딩된 문자열이라면 string 타입 사용 고려",
                )
            )

        return violations

    def _check_excessive_unions(self, schema_dict: dict[str, Any]) -> list[LintViolation]:
        """과도한 union 타입 체크

        union이 너무 많으면 복잡도 증가
        """
        fields = schema_dict.get("fields", [])
        violations: list[LintViolation] = [
            LintViolation(
                code="EXCESSIVE_UNION",
                severity=ViolationSeverity.INFO,
                rule="Union 타입은 3개 이하 권장",
                actual=f"필드 {field.get('name')}: {len(field.get('type'))}개 union",
                hint="타입 체계 단순화 또는 별도 record로 분리 고려",
            )
            for field in fields
            if isinstance(field.get("type"), list) and len(field.get("type")) > 3
        ]

        return violations

    def _check_deep_maps(
        self, schema_dict: dict[str, Any], max_depth: int = 3
    ) -> list[LintViolation]:
        """깊은 map 구조 체크

        중첩이 깊으면 직렬화/역직렬화 비용 증가
        """

        def get_depth(obj: Any, current_depth: int = 0) -> int:
            """재귀적으로 map 깊이 계산"""
            if isinstance(obj, dict):
                if obj.get("type") == "map":
                    values_type = obj.get("values")
                    return 1 + get_depth(values_type, current_depth + 1)
                elif isinstance(obj.get("type"), dict):
                    return get_depth(obj["type"], current_depth)
            return current_depth

        fields = schema_dict.get("fields", [])

        violations: list[LintViolation] = [
            LintViolation(
                code="DEEP_MAP",
                severity=ViolationSeverity.INFO,
                rule=f"Map 중첩은 {max_depth}단계 이하 권장",
                actual=f"필드 {field.get('name')}: {get_depth(field.get('type'))}단계 map",
                hint="중첩 구조 단순화 또는 flat record 구조 고려",
            )
            for field in fields
            if get_depth(field.get("type")) > max_depth
        ]

        return violations

    def to_dict(self, report: LintReport) -> dict[str, Any]:
        """LintReport를 JSON 직렬화 가능한 dict로 변환"""
        return {
            "violations": [
                {
                    "code": v.code,
                    "severity": v.severity.value,
                    "rule": v.rule,
                    "actual": v.actual,
                    "hint": v.hint,
                    "doc_url": v.doc_url,
                }
                for v in report.violations
            ],
            "pii_score": report.pii_score,
            "risk_score": report.risk_score,
        }
