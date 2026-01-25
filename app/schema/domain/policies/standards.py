"""Corporate Standards Policies"""

import re
from typing import Any

from app.schema.domain.models.lint import LintViolation, ViolationSeverity

from .base import ISchemaLintPolicy


class NamespaceStandardPolicy(ISchemaLintPolicy):
    """네임스페이스 표준 준수 체크 정책

    표준 형식: com.chiring.[team].[env]
    """

    # 표준 패턴 (예시: com.chiring으로 시작하고 최소 4마디)
    STANDARD_PATTERN = r"^com\.chiring\.[a-z0-9_]+\.[a-z0-9_]+$"

    @property
    def code(self) -> str:
        return "NAMESPACE_NOT_STANDARD"

    def check(self, schema_dict: dict[str, Any]) -> list[LintViolation]:
        """namespace 필드의 표준 패턴 준수 여부 검사"""
        violations: list[LintViolation] = []
        namespace = schema_dict.get("namespace")

        if not namespace:
            violations.append(
                LintViolation(
                    code=self.code,
                    severity=ViolationSeverity.WARN,
                    rule="스키마 네임스페이스(namespace) 정의 필요",
                    actual="namespace is missing",
                    hint="스키마의 식별성과 조직 관리를 위해 namespace를 정의하세요",
                )
            )
            return violations

        if not re.match(self.STANDARD_PATTERN, str(namespace)):
            violations.append(
                LintViolation(
                    code=self.code,
                    severity=ViolationSeverity.INFO,
                    rule="네임스페이스 표준 패턴 준수 권장",
                    actual=f"current: '{namespace}'",
                    hint="표준 형식(com.chiring.[team].[env])을 사용하세요 (예: com.chiring.order.dev)",
                )
            )

        return violations
