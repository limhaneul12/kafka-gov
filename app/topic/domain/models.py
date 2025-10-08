"""Topic Domain 모델 - 불변 도메인 엔티티 및 값 객체"""

from __future__ import annotations

import hashlib
from enum import Enum
from typing import Any, TypeAlias

import msgspec

from ...shared.domain.policy_types import DomainPolicySeverity, DomainPolicyViolation


class DomainEnvironment(str, Enum):
    """환경 타입"""

    DEV = "dev"
    STG = "stg"
    PROD = "prod"
    UNKNOWN = "unknown"  # 환경 무관 작업용


class DomainTopicAction(str, Enum):
    """토픽 액션 타입"""

    CREATE = "create"
    UPSERT = "upsert"
    UPDATE = "update"
    DELETE = "delete"


class DomainPlanAction(str, Enum):
    """계획 액션 타입"""

    CREATE = "CREATE"
    ALTER = "ALTER"
    DELETE = "DELETE"


class DomainCleanupPolicy(str, Enum):
    """토픽 정리 정책"""

    DELETE = "delete"
    COMPACT = "compact"
    COMPACT_DELETE = "compact,delete"


# 타입 별칭
TopicName: TypeAlias = str
ChangeId: TypeAlias = str
TeamName: TypeAlias = str
DocumentUrl: TypeAlias = str
KafkaMetadata: TypeAlias = dict[str, int | str | dict]  # Kafka 메타데이터 (유연한 구조)
DBMetadata: TypeAlias = dict[str, str | None]  # DB 메타데이터


class DomainTopicMetadata(msgspec.Struct):
    """토픽 메타데이터 값 객체

    Note:
        딕셔너리 변환이 필요한 경우 `msgspec.structs.asdict(instance)` 사용
    """

    owner: TeamName | None = None
    doc: DocumentUrl | None = None
    tags: tuple[str, ...] = ()


class DomainTopicConfig(msgspec.Struct):
    """토픽 설정 값 객체

    Note:
        딕셔너리 변환이 필요한 경우 `msgspec.structs.asdict(instance)` 사용
    """

    partitions: int
    replication_factor: int
    cleanup_policy: DomainCleanupPolicy = DomainCleanupPolicy.DELETE
    retention_ms: int | None = None
    min_insync_replicas: int | None = None
    max_message_bytes: int | None = None
    segment_ms: int | None = None

    def __post_init__(self) -> None:
        if self.partitions < 1:
            raise ValueError("partitions must be >= 1")
        if self.replication_factor < 1:
            raise ValueError("replication_factor must be >= 1")
        if (
            self.min_insync_replicas is not None
            and self.min_insync_replicas > self.replication_factor
        ):
            raise ValueError(
                f"min_insync_replicas ({self.min_insync_replicas}) cannot be greater than "
                f"replication_factor ({self.replication_factor})"
            )

    def to_kafka_config(self) -> dict[str, str]:
        """Kafka 설정 딕셔너리로 변환"""
        config = {
            "cleanup.policy": self.cleanup_policy.value,
        }

        if self.retention_ms is not None:
            config["retention.ms"] = str(self.retention_ms)
        if self.min_insync_replicas is not None:
            config["min.insync.replicas"] = str(self.min_insync_replicas)
        if self.max_message_bytes is not None:
            config["max.message.bytes"] = str(self.max_message_bytes)
        if self.segment_ms is not None:
            config["segment.ms"] = str(self.segment_ms)

        return config


class DomainTopicSpec(msgspec.Struct):
    """토픽 명세 엔티티"""

    name: TopicName
    action: DomainTopicAction
    config: DomainTopicConfig | None = None
    metadata: DomainTopicMetadata | None = None

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("name is required")

        if self.action == DomainTopicAction.DELETE:
            if self.config is not None:
                raise ValueError("config should not be provided for delete action")
        else:
            if not self.config:
                raise ValueError(f"config is required for {self.action} action")
            if not self.metadata:
                raise ValueError(f"metadata is required for {self.action} action")

    @property
    def environment(self) -> DomainEnvironment:
        """토픽 이름에서 환경 추출 (환경 접두사가 없으면 DEV 반환)"""
        if "." in self.name:
            env_prefix = self.name.split(".")[0]
            try:
                return DomainEnvironment(env_prefix)
            except ValueError:
                # 유효하지 않은 환경 접두사는 DEV로 간주
                return DomainEnvironment.DEV
        else:
            # 환경 접두사가 없으면 DEV
            return DomainEnvironment.DEV

    def fingerprint(self) -> str:
        """명세 지문 생성 (변경 감지용)"""
        content = f"{self.name}:{self.action}"
        if self.config:
            config_str = "|".join(
                f"{k}={v}" for k, v in sorted(self.config.to_kafka_config().items())
            )
            content += f":{config_str}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def to_dict(self) -> dict[str, Any]:
        """Struct 인스턴스를 딕셔너리로 변환"""
        return {
            field_name: (
                getattr(self, field_name).value
                if hasattr(getattr(self, field_name), "value")
                else getattr(self, field_name)
            )
            for field_name in self.__struct_fields__
        }


class DomainTopicBatch(msgspec.Struct):
    """토픽 배치 엔티티"""

    change_id: ChangeId
    env: DomainEnvironment
    specs: tuple[DomainTopicSpec, ...]

    def __post_init__(self) -> None:
        if not self.change_id:
            raise ValueError("change_id is required")
        if not self.specs:
            raise ValueError("specs cannot be empty")

        # 토픽 이름 중복 검증
        names = [spec.name for spec in self.specs]
        if len(names) != len(set(names)):
            duplicates = [name for name in names if names.count(name) > 1]
            raise ValueError(f"Duplicate topic names found: {duplicates}")

    def fingerprint(self) -> str:
        """배치의 지문 생성 (내용 기반 해시)"""
        spec_fingerprints = [spec.fingerprint() for spec in self.specs]
        content = f"{self.change_id}:{self.env.value}:{':'.join(sorted(spec_fingerprints))}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]


class DomainTopicPlanItem(msgspec.Struct):
    """토픽 계획 아이템 값 객체"""

    name: TopicName
    action: DomainPlanAction
    diff: dict[str, str]
    current_config: dict[str, str] | None = None
    target_config: dict[str, str] | None = None

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("name is required")


class DomainTopicPlan(msgspec.Struct):
    """토픽 계획 엔티티"""

    change_id: ChangeId
    env: DomainEnvironment
    items: tuple[DomainTopicPlanItem, ...]
    violations: tuple[DomainPolicyViolation, ...]

    def __post_init__(self) -> None:
        if not self.change_id:
            raise ValueError("change_id is required")

    @property
    def has_violations(self) -> bool:
        """위반 사항 존재 여부"""
        return len(self.violations) > 0

    @property
    def error_violations(self) -> tuple[DomainPolicyViolation, ...]:
        """에러 수준 위반 사항"""
        return tuple(
            v
            for v in self.violations
            if v.severity in (DomainPolicySeverity.ERROR, DomainPolicySeverity.CRITICAL)
        )

    @property
    def warning_violations(self) -> tuple[DomainPolicyViolation, ...]:
        """경고 수준 위반 사항"""
        return tuple(v for v in self.violations if v.severity == DomainPolicySeverity.WARNING)

    @property
    def can_apply(self) -> bool:
        """적용 가능 여부 (에러 위반이 없는 경우)"""
        return len(self.error_violations) == 0

    def summary(self) -> dict[str, int]:
        """계획 요약"""
        action_counts = {}
        for item in self.items:
            action_counts[item.action.value.lower() + "_count"] = (
                action_counts.get(item.action.value.lower() + "_count", 0) + 1
            )

        return {
            "total_items": len(self.items),
            "create_count": action_counts.get("create_count", 0),
            "alter_count": action_counts.get("alter_count", 0),
            "delete_count": action_counts.get("delete_count", 0),
            "violation_count": len(self.violations),
        }


class DomainTopicApplyResult(msgspec.Struct):
    """토픽 적용 결과 엔티티"""

    change_id: ChangeId
    env: DomainEnvironment
    applied: tuple[TopicName, ...]
    skipped: tuple[TopicName, ...]
    failed: tuple[dict[str, str], ...]
    audit_id: str

    def __post_init__(self) -> None:
        if not self.change_id:
            raise ValueError("change_id is required")
        if not self.audit_id:
            raise ValueError("audit_id is required")

    def summary(self) -> dict[str, int]:
        """적용 결과 요약"""
        return {
            "total_items": len(self.applied) + len(self.skipped) + len(self.failed),
            "applied_count": len(self.applied),
            "skipped_count": len(self.skipped),
            "failed_count": len(self.failed),
        }
