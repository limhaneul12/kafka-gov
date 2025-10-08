"""Connect Domain Models - Metadata"""

from datetime import datetime

import msgspec


class ConnectorMetadata(msgspec.Struct, frozen=True):
    """커넥터 메타데이터 (거버넌스용)

    Kafka Connect REST API에는 없는 메타데이터를
    별도로 저장하여 거버넌스 기능을 제공합니다.
    """

    id: str
    connect_id: str
    connector_name: str
    team: str | None = None
    tags: list[str] = []
    description: str | None = None
    owner: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
