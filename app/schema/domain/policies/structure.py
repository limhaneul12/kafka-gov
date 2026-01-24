"""Structure Policies"""

from typing import Any

from app.schema.domain.models.lint import LintViolation, ViolationSeverity

from .base import ISchemaLintPolicy


class BytesOverusePolicy(ISchemaLintPolicy):
    """bytes 타입 남용 체크 정책"""

    @property
    def code(self) -> str:
        return "BYTES_OVERUSE"

    def check(self, schema_dict: dict[str, Any]) -> list[LintViolation]:
        """bytes 타입 필드 개수 체크

        Args:
            schema_dict: Avro 스키마 딕셔너리

        Note:
            Any 사용 이유: schema_dict의 값 타입이 특정 불가(재귀적 구조)하기 때문입니다.
        """
        violations: list[LintViolation] = []
        fields = schema_dict.get("fields", [])

        bytes_count = sum(1 for f in fields if f.get("type") == "bytes")

        if bytes_count > 3:  # 임계값: 3개 이상
            violations.append(
                LintViolation(
                    code=self.code,
                    severity=ViolationSeverity.WARN,
                    rule="bytes 타입은 바이너리 전용, 문자열은 string 사용",
                    actual=f"{bytes_count}개 bytes 필드 발견",
                    hint="base64 인코딩된 문자열이라면 string 타입 사용 고려",
                )
            )

        return violations


class ExcessiveUnionPolicy(ISchemaLintPolicy):
    """과도한 Union 사용 체크 정책"""

    @property
    def code(self) -> str:
        return "EXCESSIVE_UNION"

    def check(self, schema_dict: dict[str, Any]) -> list[LintViolation]:
        """Union 타입 개수 체크

        Note:
            Any 사용 이유: field['type']이 문자열일 수도, 리스트(Union)일 수도, 딕셔너리(Complex type)일 수도 있습니다.
        """
        fields = schema_dict.get("fields", [])
        violations: list[LintViolation] = [
            LintViolation(
                code=self.code,
                severity=ViolationSeverity.INFO,
                rule="Union 타입은 3개 이하 권장",
                actual=f"필드 {field.get('name')}: {len(field.get('type'))}개 union",
                hint="타입 체계 단순화 또는 별도 record로 분리 고려",
            )
            for field in fields
            if isinstance(field.get("type"), list) and len(field.get("type")) > 3
        ]

        return violations


class DeepMapPolicy(ISchemaLintPolicy):
    """깊은 Map 중첩 체크 정책"""

    MAX_DEPTH = 3

    @property
    def code(self) -> str:
        return "DEEP_MAP"

    def check(self, schema_dict: dict[str, Any]) -> list[LintViolation]:
        """Map 중첩 깊이 체크

        Note:
            Any 사용 이유: 스키마 구조의 재귀적 탐색을 위해 불가피하게 사용됩니다.
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
                code=self.code,
                severity=ViolationSeverity.INFO,
                rule=f"Map 중첩은 {self.MAX_DEPTH}단계 이하 권장",
                actual=f"필드 {field.get('name')}: {get_depth(field.get('type'))}단계 map",
                hint="중첩 구조 단순화 또는 flat record 구조 고려",
            )
            for field in fields
            if get_depth(field.get("type")) > self.MAX_DEPTH
        ]

        return violations
