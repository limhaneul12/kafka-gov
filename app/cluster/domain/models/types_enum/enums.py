"""Cluster Domain Enums"""

from __future__ import annotations

from enum import Enum


class SecurityProtocol(str, Enum):
    """Kafka 보안 프로토콜"""

    PLAINTEXT = "PLAINTEXT"
    SSL = "SSL"
    SASL_PLAINTEXT = "SASL_PLAINTEXT"
    SASL_SSL = "SASL_SSL"


class SaslMechanism(str, Enum):
    """SASL 인증 메커니즘"""

    PLAIN = "PLAIN"
    SCRAM_SHA_256 = "SCRAM-SHA-256"
    SCRAM_SHA_512 = "SCRAM-SHA-512"
    GSSAPI = "GSSAPI"
    OAUTHBEARER = "OAUTHBEARER"
