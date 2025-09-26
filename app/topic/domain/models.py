"""Topic Domain 모델 - 불변 도메인 엔티티 및 값 객체"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import Enum
from typing import TypeAlias

from ...policy import PolicySeverity, PolicyViolation


class Environment(str, Enum):
    """환경 타입"""

    DEV = "dev"
    STG = "stg"
    PROD = "prod"


class TopicAction(str, Enum):
    """토픽 액션 타입"""

    CREATE = "create"
    UPSERT = "upsert"
    UPDATE = "update"
    DELETE = "delete"


class PlanAction(str, Enum):
    """계획 액션 타입"""

    CREATE = "CREATE"
    ALTER = "ALTER"
    DELETE = "DELETE"


class CleanupPolicy(str, Enum):
    """토픽 정리 정책"""

    DELETE = "delete"
    COMPACT = "compact"
    COMPACT_DELETE = "compact,delete"


class CompressionType(str, Enum):
    """압축 타입"""

    NONE = "none"
    GZIP = "gzip"
    SNAPPY = "snappy"
    LZ4 = "lz4"
    ZSTD = "zstd"


# 타입 별칭
TopicName: TypeAlias = str
ChangeId: TypeAlias = str
TeamName: TypeAlias = str
DocumentUrl: TypeAlias = str


@dataclass(slots=True, frozen=True)
class TopicMetadata:
    """토픽 메타데이터 값 객체"""

    owner: TeamName
    sla: str | None = None
    doc: DocumentUrl | None = None
    tags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """불변성 검증"""
        if not self.owner:
            raise ValueError("owner is required")


@dataclass(slots=True, frozen=True)
class TopicConfig:
    """토픽 설정 값 객체"""

    partitions: int
    replication_factor: int
    cleanup_policy: CleanupPolicy = CleanupPolicy.DELETE
    compression_type: CompressionType = CompressionType.ZSTD
    retention_ms: int | None = None
    min_insync_replicas: int | None = None
    max_message_bytes: int | None = None
    segment_ms: int | None = None

    def __post_init__(self) -> None:
        """설정 검증"""
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
            "compression.type": self.compression_type.value,
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


@dataclass(slots=True, frozen=True)
class TopicSpec:
    """토픽 명세 엔티티"""

    name: TopicName
    action: TopicAction
    config: TopicConfig | None = None
    metadata: TopicMetadata | None = None
    reason: str | None = None

    def __post_init__(self) -> None:
        """명세 검증"""
        if not self.name:
            raise ValueError("name is required")

        if self.action == TopicAction.DELETE:
            if not self.reason:
                raise ValueError("reason is required for delete action")
            if self.config is not None:
                raise ValueError("config should not be provided for delete action")
        else:
            if not self.config:
                raise ValueError(f"config is required for {self.action} action")
            if not self.metadata:
                raise ValueError(f"metadata is required for {self.action} action")

    @property
    def environment(self) -> Environment:
        """토픽 이름에서 환경 추출"""
        env_prefix = self.name.split(".")[0]
        return Environment(env_prefix)

    def fingerprint(self) -> str:
        """명세 지문 생성 (변경 감지용)"""
        content = f"{self.name}:{self.action}"
        if self.config:
            config_str = "|".join(
                f"{k}={v}" for k, v in sorted(self.config.to_kafka_config().items())
            )
            content += f":{config_str}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]


@dataclass(slots=True, frozen=True)
class TopicBatch:
    """토픽 배치 엔티티"""

    change_id: ChangeId
    env: Environment
    specs: tuple[TopicSpec, ...]

    def __post_init__(self) -> None:
        """배치 검증"""
        if not self.change_id:
            raise ValueError("change_id is required")
        if not self.specs:
            raise ValueError("specs cannot be empty")

        # 토픽 이름 중복 검증
        names = [spec.name for spec in self.specs]
        if len(names) != len(set(names)):
            duplicates = [name for name in names if names.count(name) > 1]
            raise ValueError(f"Duplicate topic names found: {duplicates}")

        # 환경 일관성 검증
        for spec in self.specs:
            if spec.environment != self.env:
                raise ValueError(
                    f"Topic {spec.name} environment ({spec.environment.value}) "
                    f"does not match batch environment ({self.env.value})"
                )

    def fingerprint(self) -> str:
        """배치 지문 생성"""
        spec_fingerprints = [spec.fingerprint() for spec in self.specs]
        content = f"{self.change_id}:{self.env.value}:{':'.join(sorted(spec_fingerprints))}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]


@dataclass(slots=True, frozen=True)
class TopicPlanItem:
    """토픽 계획 아이템 값 객체"""

    name: TopicName
    action: PlanAction
    diff: dict[str, str]
    current_config: dict[str, str] | None = None
    target_config: dict[str, str] | None = None

    def __post_init__(self) -> None:
        """계획 아이템 검증"""
        if not self.name:
            raise ValueError("name is required")



@dataclass(slots=True, frozen=True)
class TopicPlan:
    """토픽 계획 엔티티"""

    change_id: ChangeId
    env: Environment
    items: tuple[TopicPlanItem, ...]
    violations: tuple[PolicyViolation, ...]

    def __post_init__(self) -> None:
        """계획 검증"""
        if not self.change_id:
            raise ValueError("change_id is required")

    @property
    def has_violations(self) -> bool:
        """위반 사항 존재 여부"""
        return len(self.violations) > 0

    @property
    def error_violations(self) -> tuple[PolicyViolation, ...]:
        """에러 수준 위반 사항"""
        return tuple(v for v in self.violations if v.severity in (PolicySeverity.ERROR, PolicySeverity.CRITICAL))

    @property
    def warning_violations(self) -> tuple[PolicyViolation, ...]:
        """경고 수준 위반 사항"""
        return tuple(v for v in self.violations if v.severity == PolicySeverity.WARNING)

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


@dataclass(slots=True, frozen=True)
class TopicApplyResult:
    """토픽 적용 결과 엔티티"""

    change_id: ChangeId
    env: Environment
    applied: tuple[TopicName, ...]
    skipped: tuple[TopicName, ...]
    failed: tuple[dict[str, str], ...]
    audit_id: str

    def __post_init__(self) -> None:
        """결과 검증"""
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
