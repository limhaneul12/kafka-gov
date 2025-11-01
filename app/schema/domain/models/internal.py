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
    """스키마 버전 정보 - 내부 처리용

    jobs.md 스펙 준수: rule_set, sr_metadata 누락 없이 수집
    """

    version: int | None
    schema_id: int | None
    schema: str | None
    schema_type: str | None
    references: list[Reference]
    hash: str

    # ✨ NEW: OSS Governance 메타데이터
    canonical_hash: str | None = None  # 정규화 후 해시 (중복 감지용)
