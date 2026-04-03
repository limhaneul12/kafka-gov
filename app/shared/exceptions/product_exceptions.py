"""Data Product 도메인 예외"""

from __future__ import annotations

from app.shared.domain.value_objects import Lifecycle, ProductId
from app.shared.exceptions.base_exceptions import DomainError, NotFoundError


class DataProductError(DomainError):
    """Data Product 도메인 예외 베이스"""


class InvalidLifecycleTransitionError(DataProductError):
    """허용되지 않는 생명주기 전이"""

    def __init__(self, current: Lifecycle, target: Lifecycle) -> None:
        super().__init__(f"invalid lifecycle transition: {current.value} → {target.value}")
        self.current = current
        self.target = target


class DataProductNotFoundError(NotFoundError):
    """Data Product를 찾을 수 없음"""

    def __init__(self, product_id: ProductId) -> None:
        super().__init__("DataProduct", product_id)
        self.product_id = product_id


class DuplicateInfraBindingError(DataProductError):
    """중복 인프라 바인딩"""

    def __init__(self, infra_type: str, resource_id: str) -> None:
        super().__init__(f"duplicate binding: {infra_type}:{resource_id}")
        self.infra_type = infra_type
        self.resource_id = resource_id


class ImmutableProductError(DataProductError):
    """변경 불가능한 상태의 Data Product 수정 시도"""

    def __init__(self, lifecycle: Lifecycle, action: str) -> None:
        super().__init__(f"cannot {action} in {lifecycle.value} state")
        self.lifecycle = lifecycle
        self.action = action


class ActiveConsumersExistError(DataProductError):
    """활성 소비자가 있는 상태에서 retire 시도"""

    def __init__(self, consumer_count: int) -> None:
        super().__init__(f"cannot retire: {consumer_count} active consumer(s) remain")
        self.consumer_count = consumer_count


class ConsumerNotFoundError(DataProductError):
    """등록된 소비자를 찾을 수 없음"""

    def __init__(self, consumer_id: str) -> None:
        super().__init__(f"consumer not found: {consumer_id}")
        self.consumer_id = consumer_id


class ClassificationDowngradeError(DataProductError):
    """분류 등급 하향 시도"""

    def __init__(self, current: str, target: str) -> None:
        super().__init__(f"classification can only be elevated: {current} → {target}")
