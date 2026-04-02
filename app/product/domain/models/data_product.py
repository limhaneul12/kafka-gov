"""Data Product 도메인 모델 — 거버넌스 시스템의 1등 시민

Data Product는 비즈니스 데이터 단위를 나타낸다.
"주문 이벤트 스트림", "결제 트랜잭션 로그" 같은 비즈니스 의미를 가진 데이터가
어떤 인프라 위에서 구현되는지와 무관하게 존재하는 개념이다.

Topic, Schema, Consumer Group은 Data Product의 *구현 세부사항*이다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.shared.domain.value_objects import (
    DataClassification,
    DomainName,
    Environment,
    InfraType,
    Lifecycle,
    ProductId,
    Tag,
    TeamOwnership,
)
from app.shared.exceptions.product_exceptions import (
    ActiveConsumersExistError,
    ClassificationDowngradeError,
    ConsumerNotFoundError,
    DuplicateInfraBindingError,
    ImmutableProductError,
    InvalidLifecycleTransitionError,
)


@dataclass(frozen=True, slots=True)
class InfraBinding:
    """Data Product와 물리 인프라 간의 바인딩

    하나의 Data Product가 여러 인프라에 바인딩될 수 있다.
    예: Kafka Topic + Schema Registry Subject + S3 archive
    """

    infra_type: InfraType
    resource_id: str
    cluster_id: str | None = None
    config: dict[str, Any] | None = None

    @property
    def is_kafka(self) -> bool:
        return self.infra_type is InfraType.KAFKA_TOPIC


@dataclass(frozen=True, slots=True)
class ConsumerBinding:
    """Data Product를 소비하는 서비스/팀 등록"""

    consumer_id: str
    service_name: str
    team: TeamOwnership
    consumer_group: str | None = None
    purpose: str | None = None
    registered_at: datetime | None = None


@dataclass(slots=True)
class DataProduct:
    """Data Product — 거버넌스의 핵심 단위

    비즈니스 데이터를 나타내는 1등 시민 엔티티.
    Topic이나 Schema가 아닌, "주문 이벤트"나 "사용자 프로필 변경" 같은
    비즈니스 맥락의 데이터가 중심이 된다.

    Aggregate Root로서 자신의 불변 조건을 스스로 보장한다.
    """

    product_id: ProductId
    name: str
    description: str
    domain: DomainName
    owner: TeamOwnership
    classification: DataClassification
    environment: Environment
    lifecycle: Lifecycle

    # 물리 인프라 바인딩 (1:N)
    infra_bindings: list[InfraBinding] = field(default_factory=list)

    # 소비자 등록 (1:N)
    consumers: list[ConsumerBinding] = field(default_factory=list)

    # 카탈로그 메타데이터
    tags: list[Tag] = field(default_factory=list)
    glossary_terms: list[str] = field(default_factory=list)

    # 감사
    created_by: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None

    # ------------------------------------------------------------------ #
    # 불변 조건(Invariants)
    # ------------------------------------------------------------------ #

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("Data Product name must not be empty")
        if not self.domain:
            raise ValueError("Data Product must belong to a domain")

    # ------------------------------------------------------------------ #
    # 생명주기 전이
    # ------------------------------------------------------------------ #

    def activate(self) -> None:
        """INCUBATION → ACTIVE"""
        if self.lifecycle is not Lifecycle.INCUBATION:
            raise InvalidLifecycleTransitionError(self.lifecycle, Lifecycle.ACTIVE)
        if not self.infra_bindings:
            raise ImmutableProductError(self.lifecycle, "activate without infra binding")
        self.lifecycle = Lifecycle.ACTIVE

    def deprecate(self, reason: str) -> None:
        """ACTIVE → DEPRECATED"""
        if self.lifecycle is not Lifecycle.ACTIVE:
            raise InvalidLifecycleTransitionError(self.lifecycle, Lifecycle.DEPRECATED)
        self.lifecycle = Lifecycle.DEPRECATED

    def retire(self) -> None:
        """DEPRECATED → RETIRED"""
        if self.lifecycle is not Lifecycle.DEPRECATED:
            raise InvalidLifecycleTransitionError(self.lifecycle, Lifecycle.RETIRED)
        if self.consumers:
            raise ActiveConsumersExistError(len(self.consumers))
        self.lifecycle = Lifecycle.RETIRED

    # ------------------------------------------------------------------ #
    # 인프라 바인딩
    # ------------------------------------------------------------------ #

    def bind_infra(self, binding: InfraBinding) -> None:
        if not self.lifecycle.is_mutable:
            raise ImmutableProductError(self.lifecycle, "modify bindings")
        for existing in self.infra_bindings:
            if (
                existing.infra_type == binding.infra_type
                and existing.resource_id == binding.resource_id
            ):
                raise DuplicateInfraBindingError(binding.infra_type.value, binding.resource_id)
        self.infra_bindings.append(binding)

    def unbind_infra(self, infra_type: InfraType, resource_id: str) -> None:
        if not self.lifecycle.is_mutable:
            raise ImmutableProductError(self.lifecycle, "modify bindings")
        original_len = len(self.infra_bindings)
        self.infra_bindings = [
            b
            for b in self.infra_bindings
            if not (b.infra_type == infra_type and b.resource_id == resource_id)
        ]
        if len(self.infra_bindings) == original_len:
            raise DuplicateInfraBindingError(infra_type.value, resource_id)

    def kafka_topics(self) -> list[InfraBinding]:
        return [b for b in self.infra_bindings if b.is_kafka]

    # ------------------------------------------------------------------ #
    # 소비자 관리
    # ------------------------------------------------------------------ #

    def register_consumer(self, consumer: ConsumerBinding) -> None:
        if not self.lifecycle.is_discoverable:
            raise ImmutableProductError(self.lifecycle, "register consumer")
        for existing in self.consumers:
            if existing.consumer_id == consumer.consumer_id:
                raise ConsumerNotFoundError(consumer.consumer_id)
        self.consumers.append(consumer)

    def deregister_consumer(self, consumer_id: str) -> None:
        original_len = len(self.consumers)
        self.consumers = [c for c in self.consumers if c.consumer_id != consumer_id]
        if len(self.consumers) == original_len:
            raise ConsumerNotFoundError(consumer_id)

    # ------------------------------------------------------------------ #
    # 분류 변경 (상향만 허용 — 하향은 별도 승인 필요)
    # ------------------------------------------------------------------ #

    def elevate_classification(self, new_classification: DataClassification) -> None:
        if new_classification <= self.classification:
            raise ClassificationDowngradeError(self.classification.value, new_classification.value)
        self.classification = new_classification

    # ------------------------------------------------------------------ #
    # 쿼리
    # ------------------------------------------------------------------ #

    @property
    def is_active(self) -> bool:
        return self.lifecycle is Lifecycle.ACTIVE

    @property
    def consumer_count(self) -> int:
        return len(self.consumers)

    @property
    def has_kafka_binding(self) -> bool:
        return any(b.is_kafka for b in self.infra_bindings)
