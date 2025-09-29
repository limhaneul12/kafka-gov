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
    int_type,
    string_type,
)

# 정규표현식 상수 정의
TOPIC_NAME_PATTERN: Final[str] = r"^((dev|stg|prod)\.)[a-z0-9._-]+$"
TOPIC_PLAN_STATUS_PATTERN: Final[str] = r"^(pending|applied|failed)$"
TOPIC_PLAN_ACTION_PATTERN: Final[str] = r"^(CREATE|ALTER|DELETE)$"


# fmt: off
# ===== 토픽 관련 타입 =====
# type: ignore
TopicName: TypeAlias = string_type(desc="토픽 이름(환경 접두사 포함)", max_length=249, pattern=TOPIC_NAME_PATTERN)
TagName: TypeAlias = string_type(desc="태그 이름", max_length=50, pattern=COMMON_TAG_NAME_PATTERN)

# ===== 팀/조직 관련 타입 =====
# type: ignore
TeamName: TypeAlias = string_type(desc="팀 이름", max_length=50, pattern=COMMON_TEAM_NAME_PATTERN)
DocumentUrl: TypeAlias = string_type(desc="문서 URL", max_length=500, pattern=COMMON_DOCUMENT_URL_PATTERN)
SlaRequirement: TypeAlias = string_type(desc="SLA 요구사항", max_length=100)

# ===== 변경 관리 타입 =====
ChangeId: TypeAlias = string_type(desc="변경 ID(추적용)", max_length=100, pattern=COMMON_CHANGE_ID_PATTERN)
ReasonText: TypeAlias = string_type(desc="변경 사유", max_length=500)
PlanStatus: TypeAlias = string_type(desc="계획 상태", max_length=10, pattern=TOPIC_PLAN_STATUS_PATTERN)
PlanAction: TypeAlias = string_type(desc="실행될 액션", max_length=10, pattern=TOPIC_PLAN_ACTION_PATTERN)

# ===== 감사/로깅 타입 =====
AuditId: TypeAlias = string_type(desc="감사 로그 ID", max_length=100)

# ===== 에러/위반 타입 =====
ErrorRule: TypeAlias = string_type(desc="위반 규칙", max_length=100)
ErrorSeverity: TypeAlias = string_type(desc="심각도", max_length=10, pattern=COMMON_ERROR_SEVERITY_PATTERN)
ErrorField: TypeAlias = string_type(desc="위반 필드", max_length=100)
ErrorMessage: TypeAlias = string_type(desc="위반 메시지", max_length=500)

# ===== Kafka 설정 타입 (정수) =====
PartitionCount: TypeAlias = int_type(desc="파티션 수", ge=1, le=1000)
ReplicationFactor: TypeAlias = int_type(desc="복제 팩터", ge=1, le=10)
MinInsyncReplicas: TypeAlias = int_type(desc="최소 동기화 복제본 수", ge=1, le=10)

# ===== Kafka 성능/용량 타입 (정수) =====
RetentionMs: TypeAlias = int_type(desc="보존 시간 (밀리초)", ge=1000, le=2147483647)
SegmentMs: TypeAlias = int_type(desc="세그먼트 롤링 시간 (밀리초)", ge=1000)
MaxMessageBytes: TypeAlias = int_type(desc="최대 메시지 크기 (바이트)", ge=1000, le=100000000)
