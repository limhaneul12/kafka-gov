"""Schema Interface 타입 힌트 정의"""

from __future__ import annotations

from typing import Final, TypeAlias

from app.shared.interface.type_factory import (
    COMMON_CHANGE_ID_PATTERN,
    COMMON_DOCUMENT_URL_PATTERN,
    COMMON_ERROR_SEVERITY_PATTERN,
    COMMON_TAG_NAME_PATTERN,
    COMMON_TEAM_NAME_PATTERN,
    int_type,
    string_type,
)

# 정규표현식 상수 정의
SCHEMA_SUBJECT_PATTERN: Final[str] = r"^[a-z0-9._-]+(-key|-value)?$"
SCHEMA_REFERENCE_NAME_PATTERN: Final[str] = r"^[A-Za-z_][A-Za-z0-9_.-]*$"
SCHEMA_PLAN_ACTION_PATTERN: Final[str] = r"^(REGISTER|UPDATE|DELETE|NONE)$"
SCHEMA_URL_PATTERN: Final[str] = r"^https?://.+$"


# ===== 공통 타입 =====
ChangeId: TypeAlias = string_type(
    desc="변경 ID(추적용)", max_length=100, pattern=COMMON_CHANGE_ID_PATTERN
)
SubjectName: TypeAlias = string_type(
    desc="스키마 Subject 이름", max_length=255, pattern=SCHEMA_SUBJECT_PATTERN
)
SchemaDefinition: TypeAlias = string_type(desc="스키마 정의(JSON/SDL)", max_length=262144)
SchemaYamlText: TypeAlias = string_type(desc="스키마 YAML 정의", max_length=262144)
FileReference: TypeAlias = string_type(desc="파일 경로 또는 식별자", max_length=512)
TeamName: TypeAlias = string_type(
    desc="관리 팀 이름", max_length=50, pattern=COMMON_TEAM_NAME_PATTERN
)
DocumentUrl: TypeAlias = string_type(
    desc="문서 URL", max_length=500, pattern=COMMON_DOCUMENT_URL_PATTERN
)
ReasonText: TypeAlias = string_type(desc="변경 사유", max_length=500)
SchemaHash: TypeAlias = string_type(desc="스키마 해시(HEX)", max_length=128, min_length=8)
ReferenceName: TypeAlias = string_type(
    desc="참조 스키마 이름", max_length=255, pattern=SCHEMA_REFERENCE_NAME_PATTERN
)
ReferenceSubject: TypeAlias = string_type(
    desc="참조 Subject", max_length=255, pattern=SCHEMA_SUBJECT_PATTERN
)
SchemaVersion: TypeAlias = int_type(desc="스키마 버전", ge=1)
TagName: TypeAlias = string_type(desc="태그 이름", max_length=50, pattern=COMMON_TAG_NAME_PATTERN)
PlanAction: TypeAlias = string_type(
    desc="배치 계획 액션", max_length=16, pattern=SCHEMA_PLAN_ACTION_PATTERN
)
ErrorRule: TypeAlias = string_type(desc="위반 규칙", max_length=100)
ErrorMessage: TypeAlias = string_type(desc="위반 메시지", max_length=500)
ErrorField: TypeAlias = string_type(desc="위반 필드", max_length=100)
ErrorSeverity: TypeAlias = string_type(
    desc="위반 심각도", max_length=10, pattern=COMMON_ERROR_SEVERITY_PATTERN
)
AuditId: TypeAlias = string_type(desc="감사 로그 ID", max_length=100)
StorageUrl: TypeAlias = string_type(desc="저장소 URL", max_length=500, pattern=SCHEMA_URL_PATTERN)
