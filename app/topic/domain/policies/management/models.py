"""Policy Management Models

User-defined custom policies with versioning support.
"""

from dataclasses import dataclass
from enum import Enum


class PolicyType(str, Enum):
    """Policy type"""

    NAMING = "naming"
    GUARDRAIL = "guardrail"


class PolicyStatus(str, Enum):
    """Policy status"""

    DRAFT = "draft"  # 작성 중
    ACTIVE = "active"  # 활성 (사용 가능)
    ARCHIVED = "archived"  # 보관 (더 이상 사용 안 함)


@dataclass(frozen=True, slots=True)
class StoredPolicy:
    """Stored custom policy with versioning - Entity

    사용자가 UI에서 생성한 커스텀 정책을 DB에 저장하는 모델
    """

    # Required fields (no defaults)
    policy_id: str  # UUID
    policy_type: PolicyType
    name: str  # 정책 이름 (예: "financial-critical", "dev-team-standard")
    description: str
    version: int  # 버전 번호 (1, 2, 3...)
    status: PolicyStatus

    # 정책 내용 (JSON으로 직렬화)
    # - naming일 경우: CustomNamingRules의 dict
    # - guardrail일 경우: CustomGuardrailPreset의 dict
    content: dict[str, str | int | bool | list[str]]

    created_by: str
    created_at: str  # ISO 8601

    # Optional fields (with defaults) - MUST come after required fields
    # 적용 환경 (dev, stg, prod, total)
    # - dev: Development 환경 전용
    # - stg: Staging 환경 전용
    # - prod: Production 환경 전용
    # - total: 모든 환경 공통 (global)
    target_environment: str = "total"
    updated_at: str | None = None
    activated_at: str | None = None  # 활성화 시간 (ACTIVE 상태가 된 시점)


@dataclass(frozen=True, slots=True)
class PolicyReference:
    """Policy reference for topic creation - Value Object

    토픽 생성 시 어떤 정책을 사용할지 지정
    """

    # 3가지 옵션:
    # 1. None → 정책 없음 (검증 스킵)
    # 2. preset="dev" → 프리셋 사용
    # 3. policy_id="uuid" → 커스텀 정책 사용

    preset: str | None = None  # "dev", "stg", "prod"
    policy_id: str | None = None  # Custom policy UUID

    def __post_init__(self) -> None:
        """Validate: preset과 policy_id 중 하나만 사용"""
        if self.preset and self.policy_id:
            raise ValueError("Cannot use both preset and policy_id")
