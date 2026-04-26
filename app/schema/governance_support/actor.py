from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from app.schema.governance_support.roles import DEFAULT_USER


def _clean_actor_value(value: str | None) -> str | None:
    if value is None:
        return None

    normalized = value.strip()
    if not normalized:
        return None

    return normalized


def _get_header_value(headers: Mapping[str, str] | None, *names: str) -> str | None:
    if headers is None:
        return None

    for name in names:
        value = headers.get(name)
        if value is not None:
            return value
        value = headers.get(name.lower())
        if value is not None:
            return value

    return None


@dataclass(frozen=True, slots=True)
class ActorContext:
    user_id: str | None = None
    username: str | None = None
    source: str | None = None

    @property
    def actor(self) -> str:
        return self.username or self.user_id or DEFAULT_USER

    def as_metadata(self) -> dict[str, str]:
        metadata: dict[str, str] = {}
        if self.user_id is not None:
            metadata["user_id"] = self.user_id
        if self.username is not None:
            metadata["username"] = self.username
        if self.source is not None:
            metadata["source"] = self.source
        return metadata


def actor_context_from_headers(
    headers: Mapping[str, str] | None,
    *,
    default_source: str = "api",
) -> ActorContext:
    return ActorContext(
        user_id=_clean_actor_value(
            _get_header_value(headers, "X-User-Id", "X-Actor-Id", "X-User-ID")
        ),
        username=_clean_actor_value(
            _get_header_value(headers, "X-Username", "X-Forwarded-User", "X-Actor")
        ),
        source=_clean_actor_value(_get_header_value(headers, "X-Actor-Source")) or default_source,
    )


def actor_context_dict(
    actor_context: ActorContext | Mapping[str, str] | None,
) -> dict[str, str] | None:
    if actor_context is None:
        return None

    if isinstance(actor_context, ActorContext):
        metadata = actor_context.as_metadata()
        return metadata or None

    metadata = {
        key: value.strip()
        for key, value in actor_context.items()
        if isinstance(key, str) and isinstance(value, str) and value.strip()
    }
    return metadata or None


def merge_actor_metadata(
    snapshot: Mapping[str, Any] | None,
    actor_context: ActorContext | Mapping[str, str] | None,
) -> dict[str, Any]:
    merged = dict(snapshot or {})
    metadata = actor_context_dict(actor_context)
    if metadata is not None:
        merged["actor_context"] = metadata
    return merged
