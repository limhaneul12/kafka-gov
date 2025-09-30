"""In-Memory Event Bus - 간단하고 효율적인 이벤트 발행/구독"""

from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Awaitable, Callable
from typing import Any

logger = logging.getLogger(__name__)


class EventBus:
    """In-Memory Event Bus - 동기식 이벤트 처리"""

    def __init__(self) -> None:
        self._handlers: dict[str, list[Callable[[Any], Awaitable[None] | None]]] = defaultdict(list)

    def subscribe(self, event_type: str, handler: Callable[[Any], Awaitable[None] | None]) -> None:
        """이벤트 핸들러 등록"""
        self._handlers[event_type].append(handler)
        logger.info(f"Handler registered for event: {event_type}")

    async def publish(self, event: Any) -> None:
        """이벤트 발행 - 모든 핸들러 실행"""
        event_type = event.event_type
        handlers = self._handlers.get(event_type, [])

        if not handlers:
            logger.warning(f"No handlers registered for event: {event_type}")
            return

        logger.info(f"Publishing event: {event_type} (aggregate_id={event.aggregate_id})")

        for handler in handlers:
            try:
                result = handler(event)
                # async 핸들러 지원
                if result is not None and hasattr(result, "__await__"):
                    await result
            except Exception as e:
                logger.error(f"Handler failed for event {event_type}: {e}", exc_info=True)
                # 한 핸들러 실패해도 다른 핸들러는 계속 실행


# 싱글톤 인스턴스
_event_bus_instance: EventBus | None = None


def get_event_bus() -> EventBus:
    """Event Bus 싱글톤 인스턴스 반환"""
    global _event_bus_instance
    if _event_bus_instance is None:
        _event_bus_instance = EventBus()
    return _event_bus_instance
