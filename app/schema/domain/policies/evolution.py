"""Evolution & Compatibility Policies"""

from typing import Any

from app.schema.domain.models.lint import LintViolation, ViolationSeverity

from .base import ISchemaLintPolicy


class NullableDefaultPolicy(ISchemaLintPolicy):
    """Nullable 필드에 대한 Default 값 존재 여부 체크 정책

    Avro에서는 필드를 추가할 때 해당 필드가 Nullable(Union with null)이라면,
    반드시 default 값을 지정해야 이전 버전의 데이터를 읽을 때 에러가 발생하지 않습니다.
    """

    @property
    def code(self) -> str:
        return "NULLABLE_DEFAULT_MISSING"

    def check(self, schema_dict: dict[str, Any]) -> list[LintViolation]:
        """Union 타입에 'null'이 포함된 필드의 default 값 존재 여부 검사"""
        violations: list[LintViolation] = []
        fields = schema_dict.get("fields", [])

        if not isinstance(fields, list):
            return violations

        for field in fields:
            field_name = field.get("name", "unknown")
            field_type = field.get("type")

            # 1. Union 타입인지 확인 (리스트 형태)
            if isinstance(field_type, list):
                # 2. Union 안에 'null'이 포함되어 있는지 확인
                if "null" in field_type:
                    # 3. default 키가 존재하는지 확인
                    if "default" not in field:
                        violations.append(
                            LintViolation(
                                code=self.code,
                                severity=ViolationSeverity.WARN,
                                rule="Nullable 필드(Union with null)는 반드시 default 값을 가져야 함",
                                actual=f"field '{field_name}' is nullable but has no default",
                                hint=f"'{field_name}' 필드에 'default': null 속성을 추가하세요 (호환성 사고 방지)",
                            )
                        )

        return violations
