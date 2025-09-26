"""정책 팩토리 - 기본 정책 생성"""

from __future__ import annotations

from ..domain import (
    ConfigurationRule,
    Environment,
    NamingRule,
    PolicySet,
    ResourceType,
)


class DefaultPolicyFactory:
    """기본 정책 팩토리"""

    @staticmethod
    def create_topic_policies() -> dict[Environment, PolicySet]:
        """Topic 기본 정책 생성"""
        policies = {}

        # DEV 환경
        dev_rules = (
            NamingRule(
                pattern=r"^dev\.[a-z0-9._-]+$",
                forbidden_prefixes=(),
            ),
            ConfigurationRule(
                config_key="partitions",
                min_value=1,
                max_value=12,
                required=True,
            ),
            ConfigurationRule(
                config_key="replication.factor",
                min_value=1,
                max_value=3,
                required=True,
            ),
            ConfigurationRule(
                config_key="retention.ms",
                max_value=259200000,  # 3일
                required=False,
            ),
            ConfigurationRule(
                config_key="compression.type",
                allowed_values=("zstd", "lz4", "snappy", "gzip"),
                required=False,
            ),
        )
        policies[Environment.DEV] = PolicySet(
            environment=Environment.DEV,
            resource_type=ResourceType.TOPIC,
            rules=dev_rules,
        )

        # STG 환경
        stg_rules = (
            NamingRule(
                pattern=r"^stg\.[a-z0-9._-]+$",
                forbidden_prefixes=("tmp.", "test."),
            ),
            ConfigurationRule(
                config_key="partitions",
                min_value=1,
                max_value=24,
                required=True,
            ),
            ConfigurationRule(
                config_key="replication.factor",
                min_value=2,
                max_value=3,
                required=True,
            ),
            ConfigurationRule(
                config_key="retention.ms",
                min_value=86400000,  # 1일
                max_value=604800000,  # 7일
                required=False,
            ),
            ConfigurationRule(
                config_key="compression.type",
                allowed_values=("zstd", "lz4"),
                required=False,
            ),
        )
        policies[Environment.STG] = PolicySet(
            environment=Environment.STG,
            resource_type=ResourceType.TOPIC,
            rules=stg_rules,
        )

        # PROD 환경
        prod_rules = (
            NamingRule(
                pattern=r"^prod\.[a-z0-9._-]+$",
                forbidden_prefixes=("tmp.", "test.", "debug."),
            ),
            ConfigurationRule(
                config_key="partitions",
                min_value=3,
                max_value=48,
                required=True,
            ),
            ConfigurationRule(
                config_key="replication.factor",
                min_value=3,
                required=True,
            ),
            ConfigurationRule(
                config_key="min.insync.replicas",
                min_value=2,
                required=True,
            ),
            ConfigurationRule(
                config_key="retention.ms",
                min_value=604800000,  # 7일
                required=False,
            ),
            ConfigurationRule(
                config_key="compression.type",
                allowed_values=("zstd",),
                required=True,
            ),
        )
        policies[Environment.PROD] = PolicySet(
            environment=Environment.PROD,
            resource_type=ResourceType.TOPIC,
            rules=prod_rules,
        )

        return policies

    @staticmethod
    def create_schema_policies() -> dict[Environment, PolicySet]:
        """Schema 기본 정책 생성"""
        policies = {}

        # DEV 환경
        dev_rules = (
            NamingRule(
                pattern=r"^dev\.[a-z0-9._-]+(-key|-value)?$",
                forbidden_prefixes=(),
            ),
        )
        policies[Environment.DEV] = PolicySet(
            environment=Environment.DEV,
            resource_type=ResourceType.SCHEMA,
            rules=dev_rules,
        )

        # STG 환경
        stg_rules = (
            NamingRule(
                pattern=r"^stg\.[a-z0-9._-]+(-key|-value)?$",
                forbidden_prefixes=("tmp.", "test."),
            ),
        )
        policies[Environment.STG] = PolicySet(
            environment=Environment.STG,
            resource_type=ResourceType.SCHEMA,
            rules=stg_rules,
        )

        # PROD 환경
        prod_rules = (
            NamingRule(
                pattern=r"^prod\.[a-z0-9._-]+(-key|-value)?$",
                forbidden_prefixes=("tmp.", "test.", "debug."),
            ),
        )
        policies[Environment.PROD] = PolicySet(
            environment=Environment.PROD,
            resource_type=ResourceType.SCHEMA,
            rules=prod_rules,
        )

        return policies
