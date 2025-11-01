"""전략 레지스트리 (싱글톤)

3가지 축의 전략을 등록/조회합니다.
"""

from __future__ import annotations

import logging

from .schema import (
    CompactRecordStrategyInput,
    EnvPrefixedStrategyInput,
    RecordNameStrategyInput,
    StrategyAxis,
    StrategyDescriptor,
    TeamScopedStrategyInput,
    TopicNameStrategyInput,
    TopicRecordNameStrategyInput,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Strategy Descriptors (전략 메타데이터)
# ============================================================================

_SR_BUILT_IN_STRATEGIES = {
    "TopicNameStrategy": StrategyDescriptor(
        id="builtin:TopicNameStrategy",
        axis=StrategyAxis.SR_BUILT_IN,
        key="TopicNameStrategy",
        name="Topic Name Strategy",
        description="Subject format: <topic>-<key|value>",
    ),
    "RecordNameStrategy": StrategyDescriptor(
        id="builtin:RecordNameStrategy",
        axis=StrategyAxis.SR_BUILT_IN,
        key="RecordNameStrategy",
        name="Record Name Strategy",
        description="Subject format: <namespace>.<record>",
    ),
    "TopicRecordNameStrategy": StrategyDescriptor(
        id="builtin:TopicRecordNameStrategy",
        axis=StrategyAxis.SR_BUILT_IN,
        key="TopicRecordNameStrategy",
        name="Topic Record Name Strategy",
        description="Subject format: <topic>-<namespace>.<record>",
    ),
}

_GOV_STRATEGIES = {
    "EnvPrefixed": StrategyDescriptor(
        id="gov:EnvPrefixed",
        axis=StrategyAxis.GOV,
        key="EnvPrefixed",
        name="Environment Prefixed Strategy",
        description="Subject format: <env>.<topic>-<namespace>.<record>",
    ),
    "TeamScoped": StrategyDescriptor(
        id="gov:TeamScoped",
        axis=StrategyAxis.GOV,
        key="TeamScoped",
        name="Team Scoped Strategy",
        description="Subject format: <team>.<namespace>.<record>",
    ),
    "CompactRecord": StrategyDescriptor(
        id="gov:CompactRecord",
        axis=StrategyAxis.GOV,
        key="CompactRecord",
        name="Compact Record Strategy",
        description="Subject format: <record> (for dev/local only)",
    ),
}

# Input 클래스 매핑
_INPUT_CLASS_MAP = {
    "builtin:TopicNameStrategy": TopicNameStrategyInput,
    "builtin:RecordNameStrategy": RecordNameStrategyInput,
    "builtin:TopicRecordNameStrategy": TopicRecordNameStrategyInput,
    "gov:EnvPrefixed": EnvPrefixedStrategyInput,
    "gov:TeamScoped": TeamScopedStrategyInput,
    "gov:CompactRecord": CompactRecordStrategyInput,
}


# ============================================================================
# Registry
# ============================================================================


class StrategyRegistry:
    """Subject 전략 레지스트리"""

    def __init__(self) -> None:
        self._strategies: dict[str, StrategyDescriptor] = {}
        self._bootstrapped = False

    def bootstrap(self) -> None:
        """빌트인/GOV 전략 등록 (Idempotent)"""
        if self._bootstrapped:
            logger.debug("Strategy registry already bootstrapped, skipping")
            return

        # SR_BUILT_IN
        for descriptor in _SR_BUILT_IN_STRATEGIES.values():
            self._strategies[descriptor.id] = descriptor

        # GOV
        for descriptor in _GOV_STRATEGIES.values():
            self._strategies[descriptor.id] = descriptor

        self._bootstrapped = True
        logger.info(f"Strategy registry bootstrapped with {len(self._strategies)} strategies")

    def get_descriptor(self, strategy_id: str) -> StrategyDescriptor | None:
        """전략 메타데이터 조회"""
        return self._strategies.get(strategy_id)

    def get_input_class(self, strategy_id: str) -> type | None:
        """전략 Input 클래스 조회"""
        return _INPUT_CLASS_MAP.get(strategy_id)

    def list_by_axis(self, axis: StrategyAxis) -> list[StrategyDescriptor]:
        """축별 전략 목록"""
        return [s for s in self._strategies.values() if s.axis == axis]

    def list_all(self) -> list[StrategyDescriptor]:
        """전체 전략 목록"""
        return list(self._strategies.values())

    def list_sr_built_in(self) -> list[StrategyDescriptor]:
        """SR_BUILT_IN 전략 목록"""
        return self.list_by_axis(StrategyAxis.SR_BUILT_IN)

    def list_gov(self) -> list[StrategyDescriptor]:
        """GOV 전략 목록"""
        return self.list_by_axis(StrategyAxis.GOV)

    def list_custom(self) -> list[StrategyDescriptor]:
        """CUSTOM 전략 목록 (향후)"""
        return self.list_by_axis(StrategyAxis.CUSTOM)


# ============================================================================
# Singleton
# ============================================================================

_registry: StrategyRegistry | None = None


def get_registry() -> StrategyRegistry:
    """전역 레지스트리 (싱글톤)"""
    global _registry
    if _registry is None:
        _registry = StrategyRegistry()
        _registry.bootstrap()
    return _registry
