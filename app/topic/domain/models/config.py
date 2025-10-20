"""Topic Config and Metadata Models"""

from __future__ import annotations

from dataclasses import dataclass

from .types_enum import DocumentUrl, DomainCleanupPolicy, TeamName


@dataclass(slots=True)
class DomainTopicMetadata:
    """토픽 메타데이터 - Value Object (mutable)

    Note:
        dataclasses.asdict() 사용
    """

    owners: tuple[TeamName, ...] = ()
    doc: DocumentUrl | None = None
    tags: tuple[str, ...] = ()
    slo: str | None = None
    sla: str | None = None


@dataclass(slots=True)
class DomainTopicConfig:
    """토픽 설정 - Value Object (mutable)

    Note:
        dataclasses.asdict() 사용
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
