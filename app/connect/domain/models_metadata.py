"""Connect Domain Models - Metadata"""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class ConnectorMetadata:
    """커넥터 메타데이터 (거버넌스용) - Value Object

    Kafka Connect REST API에는 없는 메타데이터를
    별도로 저장하여 거버넌스 기능을 제공합니다.
    """

    id: str
    connect_id: str
    connector_name: str
    team: str | None = None
    tags: list[str] = None  # type: ignore
    description: str | None = None
    owner: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.tags is None:
            object.__setattr__(self, "tags", [])
