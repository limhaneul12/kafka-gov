"""Repository 인터페이스 모듈"""

from .interfaces import (
    IAuditRepository,
    IPolicyRepository,
    ITopicMetadataRepository,
    ITopicRepository,
)

__all__ = [
    "IAuditRepository",
    "IPolicyRepository",
    "ITopicMetadataRepository",
    "ITopicRepository",
]
