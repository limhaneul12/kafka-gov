"""Topic Spec and Batch Models"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from .config import DomainTopicConfig, DomainTopicMetadata
from .types_enum import ChangeId, DomainEnvironment, DomainTopicAction, TopicName


@dataclass(frozen=True, slots=True)
class DomainTopicSpec:
    """토픽 명세 - Value Object (immutable)"""

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


@dataclass(frozen=True, slots=True)
class DomainTopicBatch:
    """토픽 배치 - Aggregate Root (immutable)"""

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
