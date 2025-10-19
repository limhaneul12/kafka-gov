"""Schema Internal Models (for infrastructure layer)"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Reference:
    """스키마 참조 - 내부 처리용"""

    name: str
    subject: str
    version: int

    def to_dict(self) -> dict[str, int | str]:
        return {
            "name": self.name,
            "subject": self.subject,
            "version": self.version,
        }


@dataclass(slots=True)
class SchemaVersionInfo:
    """스키마 버전 정보 - 내부 처리용"""

    version: int | None
    schema_id: int | None
    schema: str | None
    schema_type: str | None
    references: list[Reference]
    hash: str
