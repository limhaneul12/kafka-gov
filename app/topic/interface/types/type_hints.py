# type: ignore

"""Topic Interface 타입 힌트 정의"""

from __future__ import annotations

from typing import Final, TypeAlias

from app.shared.interface.type_factory import (
    COMMON_CHANGE_ID_PATTERN,
    COMMON_DOCUMENT_URL_PATTERN,
    COMMON_ERROR_SEVERITY_PATTERN,
    COMMON_TAG_NAME_PATTERN,
    COMMON_TEAM_NAME_PATTERN,
    string_type,
)

# 정규표현식 상수 정의
# 토픽 이름: 대소문자, 숫자, 점(.), 밑줄(_), 하이픈(-) 허용
TOPIC_NAME_PATTERN: Final[str] = r"^[a-zA-Z0-9_.-]+$"
TOPIC_PLAN_STATUS_PATTERN: Final[str] = r"^(pending|applied|failed)$"
TOPIC_PLAN_ACTION_PATTERN: Final[str] = r"^(CREATE|ALTER|DELETE)$"


# fmt: off
# ===== 토픽 관련 타입 =====
# type: ignore
TopicName: TypeAlias = string_type(desc="토픽 이름", max_length=249, pattern=TOPIC_NAME_PATTERN)
TagName: TypeAlias = string_type(desc="태그 이름", max_length=50, pattern=COMMON_TAG_NAME_PATTERN)

# ===== 팀/조직 관련 타입 =====
# type: ignore
TeamName: TypeAlias = string_type(desc="팀 이름", max_length=50, pattern=COMMON_TEAM_NAME_PATTERN)
DocumentUrl: TypeAlias = string_type(desc="문서 URL", max_length=500, pattern=COMMON_DOCUMENT_URL_PATTERN)

# ===== 변경 관리 타입 =====
ChangeId: TypeAlias = string_type(desc="변경 ID(추적용)", max_length=100, pattern=COMMON_CHANGE_ID_PATTERN)
PlanStatus: TypeAlias = string_type(desc="계획 상태", max_length=10, pattern=TOPIC_PLAN_STATUS_PATTERN)
PlanAction: TypeAlias = string_type(desc="실행될 액션", max_length=10, pattern=TOPIC_PLAN_ACTION_PATTERN)

# ===== 감사/로깅 타입 =====
AuditId: TypeAlias = string_type(desc="감사 로그 ID", max_length=100)

# ===== 에러/위반 타입 =====
ErrorRule: TypeAlias = string_type(desc="위반 규칙", max_length=100)
ErrorSeverity: TypeAlias = string_type(desc="심각도", max_length=10, pattern=COMMON_ERROR_SEVERITY_PATTERN)
ErrorField: TypeAlias = string_type(desc="위반 필드", max_length=100)
ErrorMessage: TypeAlias = string_type(desc="위반 메시지", max_length=500)
