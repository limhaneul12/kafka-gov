"""Security Policies"""

from typing import Any, ClassVar

from app.schema.domain.models.lint import LintViolation, ViolationSeverity

from .base import ISchemaLintPolicy


class PiiCandidatePolicy(ISchemaLintPolicy):
    """PII(개인 식별 정보) 후보 감지 정책"""

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

    @property
    def code(self) -> str:
        return "PII_CANDIDATE"

    def check(self, schema_dict: dict[str, Any]) -> list[LintViolation]:
        """PII 후보 필드 태깅

        Args:
            schema_dict: Avro 스키마 딕셔너리

        Note:
            Any 사용 이유: schema_dict["fields"]는 리스트이고, 그 내부 요소는 dict[str, Any] 등 복잡한 구조입니다.
        """
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
                        code=self.code,
                        severity=ViolationSeverity.INFO,
                        rule="PII 가능성이 있는 필드명",
                        actual=f"필드: {field.get('name')}, 키워드: {matched_keywords}",
                        hint="민감 데이터라면 암호화/마스킹 고려",
                        doc_url="https://kafka-gov.example.com/docs/pii-handling",
                    )
                )

        return violations
