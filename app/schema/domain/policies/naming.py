"""Naming Policies"""

import re
from typing import Any

from app.schema.domain.models.lint import LintViolation, ViolationSeverity

from .base import ISchemaLintPolicy


class FieldNamingPolicy(ISchemaLintPolicy):
    """필드 네이밍 일관성 체크 정책 (snake_case vs camelCase)"""

    @property
    def code(self) -> str:
        return "NAMING_INCONSISTENT"

    def check(self, schema_dict: dict[str, Any]) -> list[LintViolation]:
        """필드 네이밍 일관성 체크

        Args:
            schema_dict: Avro 스키마 딕셔너리

        Note:
            Any 사용 이유: schema_dict의 값들은 다양한 타입(str, list, dict 등)이 올 수 있어 Any를 사용합니다.
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
                    code=self.code,
                    severity=ViolationSeverity.WARN,
                    rule="필드명은 snake_case 또는 camelCase 중 하나로 통일",
                    actual=f"snake_case: {snake_count}, camelCase: {camel_count}",
                    hint="Avro는 snake_case 권장 (Kafka 관례)",
                )
            )

        return violations
