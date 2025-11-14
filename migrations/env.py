import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

# ---- Project metadata import ----
# NOTE: Base.metadata must include all Table definitions for autogenerate.
from app.shared.settings import settings
from app.shared.database import Base

# If needed, import models so they are registered on Base.metadata
from app.topic.infrastructure.models import (
    TopicMetadataModel,
    TopicPlanModel,
    TopicApplyResultModel,
    AuditLogModel,
    TopicPartitionMetrics,
    LeaderDistribution,
    MetricsSnapshot,
    PolicyModel,
)
from app.schema.infrastructure.models import (
    SchemaApplyResultModel,
    SchemaMetadataModel,
    SchemaPlanModel,
    SchemaArtifactModel,
    SchemaUploadResultModel,
    SchemaAuditLogModel,
)
from app.cluster.infrastructure.models import (
    KafkaClusterModel,
    KafkaConnectModel,
    SchemaRegistryModel,
)
from app.connect.infrastructure.models import ConnectorMetadataModel
from app.consumer.infrastructure.models import (
    ConsumerGroupSnapshotModel,
    ConsumerMemberSnapshotModel,
    ConsumerPartitionSnapshotModel,
    ConsumerGroupRebalanceDeltaModel,
    ConsumerGroupRebalanceRollupModel,
)

config = context.config

# Logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata for autogenerate
target_metadata = Base.metadata


def do_run_migrations(connection):
    """Run migrations in sync context (invoked via run_sync)."""
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations in 'online' (async) mode.

    Note:
        앱 실행과 동일한 설정 경로(settings.database.url)를 사용해
        Alembic 마이그레이션 대상으로 선택된 DB에 접속한다.
    """
    async_url = settings.database.url
    config.set_main_option("sqlalchemy.url", async_url)

    engine = create_async_engine(async_url, pool_pre_ping=True)

    async with engine.connect() as async_conn:
        await async_conn.run_sync(do_run_migrations)

    await engine.dispose()


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = settings.database.url
    config.set_main_option("sqlalchemy.url", url)

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
