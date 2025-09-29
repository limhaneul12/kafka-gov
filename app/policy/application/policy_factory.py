"""정책 팩토리 - 기본 정책 생성"""

from __future__ import annotations

from ..domain import (
    DomainConfigurationRule,
    DomainEnvironment,
    DomainNamingRule,
    DomainPolicySet,
    DomainResourceType,
)


class DefaultPolicyFactory:
    """기본 정책 팩토리"""

    @staticmethod
    def create_topic_policies() -> dict[DomainEnvironment, DomainPolicySet]:
        """Topic 기본 정책 생성"""
        policies = {}

        # DEV 환경
        dev_rules = (
            DomainNamingRule(
                pattern=r"^dev\.[a-z0-9._-]+$",
                forbidden_prefixes=(),
            ),
            DomainConfigurationRule(
                config_key="partitions",
                min_value=1,
                max_value=12,
                required=True,
            ),
            DomainConfigurationRule(
                config_key="replication.factor",
                min_value=1,
                max_value=3,
                required=True,
            ),
            DomainConfigurationRule(
                config_key="retention.ms",
                max_value=259200000,  # 3일
                required=False,
            ),
            DomainConfigurationRule(
                config_key="compression.type",
                allowed_values=("zstd", "lz4", "snappy", "gzip"),
                required=False,
            ),
        )
        policies[DomainEnvironment.DEV] = DomainPolicySet(
            environment=DomainEnvironment.DEV,
            resource_type=DomainResourceType.TOPIC,
            rules=dev_rules,
        )

        # STG 환경
        stg_rules = (
            DomainNamingRule(
                pattern=r"^stg\.[a-z0-9._-]+$",
                forbidden_prefixes=("tmp.", "test."),
            ),
            DomainConfigurationRule(
                config_key="partitions",
                min_value=1,
                max_value=24,
                required=True,
            ),
            DomainConfigurationRule(
                config_key="replication.factor",
                min_value=2,
                max_value=3,
                required=True,
            ),
            DomainConfigurationRule(
                config_key="retention.ms",
                min_value=86400000,  # 1일
                max_value=604800000,  # 7일
                required=False,
            ),
            DomainConfigurationRule(
                config_key="compression.type",
                allowed_values=("zstd", "lz4"),
                required=False,
            ),
        )
        policies[DomainEnvironment.STG] = DomainPolicySet(
            environment=DomainEnvironment.STG,
            resource_type=DomainResourceType.TOPIC,
            rules=stg_rules,
        )

        # PROD 환경
        prod_rules = (
            DomainNamingRule(
                pattern=r"^prod\.[a-z0-9._-]+$",
                forbidden_prefixes=("tmp.", "test.", "debug."),
            ),
            DomainConfigurationRule(
                config_key="partitions",
                min_value=3,
                max_value=48,
                required=True,
            ),
            DomainConfigurationRule(
                config_key="replication.factor",
                min_value=3,
                required=True,
            ),
            DomainConfigurationRule(
                config_key="min.insync.replicas",
                min_value=2,
                required=True,
            ),
            DomainConfigurationRule(
                config_key="retention.ms",
                min_value=604800000,  # 7일
                required=False,
            ),
            DomainConfigurationRule(
                config_key="compression.type",
                allowed_values=("zstd",),
                required=True,
            ),
        )
        policies[DomainEnvironment.PROD] = DomainPolicySet(
            environment=DomainEnvironment.PROD,
            resource_type=DomainResourceType.TOPIC,
            rules=prod_rules,
        )

        return policies

    @staticmethod
    def create_schema_policies() -> dict[DomainEnvironment, DomainPolicySet]:
        """Schema 기본 정책 생성"""
        policies = {}

        # DEV 환경
        dev_rules = (
            DomainNamingRule(
                pattern=r"^dev\.[a-z0-9._-]+(-key|-value)?$",
                forbidden_prefixes=(),
            ),
        )
        policies[DomainEnvironment.DEV] = DomainPolicySet(
            environment=DomainEnvironment.DEV,
            resource_type=DomainResourceType.SCHEMA,
            rules=dev_rules,
        )

        # STG 환경
        stg_rules = (
            DomainNamingRule(
                pattern=r"^stg\.[a-z0-9._-]+(-key|-value)?$",
                forbidden_prefixes=("tmp.", "test."),
            ),
        )
        policies[DomainEnvironment.STG] = DomainPolicySet(
            environment=DomainEnvironment.STG,
            resource_type=DomainResourceType.SCHEMA,
            rules=stg_rules,
        )

        # PROD 환경
        prod_rules = (
            DomainNamingRule(
                pattern=r"^prod\.[a-z0-9._-]+(-key|-value)?$",
                forbidden_prefixes=("tmp.", "test.", "debug."),
            ),
        )
        policies[DomainEnvironment.PROD] = DomainPolicySet(
            environment=DomainEnvironment.PROD,
            resource_type=DomainResourceType.SCHEMA,
            rules=prod_rules,
        )

        return policies
