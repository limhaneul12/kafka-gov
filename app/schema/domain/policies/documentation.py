"""Documentation Policies"""

from typing import Any

from app.schema.domain.models.lint import LintViolation, ViolationSeverity

from .base import ISchemaLintPolicy


class SchemaDocPolicy(ISchemaLintPolicy):
    """스키마 및 필드 doc(설명) 존재 여부 체크 정책"""

    @property
    def code(self) -> str:
        return "MISSING_DOC"

    def check(self, schema_dict: dict[str, Any]) -> list[LintViolation]:
        """스키마 및 모든 필드에 doc 필드가 있는지 검사

        Args:
            schema_dict: Avro 스키마 딕셔너리
        """
        violations: list[LintViolation] = []

        # 1. 메인 레코드 doc 체크
        if not schema_dict.get("doc"):
            violations.append(
                LintViolation(
                    code=self.code,
                    severity=ViolationSeverity.WARN,
                    rule="스키마 메타데이터에는 doc(설명)이 포함되어야 함",
                    actual="schema doc is missing",
                    hint="스키마의 용도와 관리 주체를 doc 필드에 기록하세요",
                )
            )

        # 2. 개별 필드 doc 체크
        fields = schema_dict.get("fields", [])
        if not isinstance(fields, list):
            return violations

        for field in fields:
            if not field.get("doc"):
                field_name = field.get("name", "unknown")
                violations.append(
                    LintViolation(
                        code=self.code,
                        severity=ViolationSeverity.INFO,
                        rule=f"필드 '{field_name}'에 대한 doc(설명) 권장",
                        actual=f"field '{field_name}' doc is missing",
                        hint=f"'{field_name}' 필드가 어떤 데이터를 의미하는지 doc 필드에 기록하세요",
                    )
                )

        return violations
