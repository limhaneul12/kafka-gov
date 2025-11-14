import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

# ---- Project metadata import ----
# NOTE: Base.metadata must include all Table definitions for autogenerate.
from app.shared.settings import settings  # noqa: F401
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

# Alembic Config
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
    """Run migrations in 'online' (async) mode."""
    cfg = config.get_section(config.config_ini_section) or {}
    async_url = cfg.get("sqlalchemy.url")
    if not async_url:
        raise RuntimeError("sqlalchemy.url is not configured in alembic.ini")

    engine = create_async_engine(async_url, pool_pre_ping=True)

    async with engine.connect() as async_conn:
        await async_conn.run_sync(do_run_migrations)

    await engine.dispose()


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    if not url:
        raise RuntimeError("sqlalchemy.url is not configured in alembic.ini")

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
