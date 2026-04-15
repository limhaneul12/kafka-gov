"""Schema Registry connection repository implementation."""

from __future__ import annotations

import logging
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.registry_connections.domain.models import SchemaRegistry
from app.registry_connections.domain.repositories import ISchemaRegistryRepository

from .models import SchemaRegistryModel

logger = logging.getLogger(__name__)
SessionFactory = Callable[..., AbstractAsyncContextManager[AsyncSession]]


class MySQLSchemaRegistryRepository(ISchemaRegistryRepository):
    def __init__(self, session_factory: SessionFactory) -> None:
        self.session_factory = session_factory

    async def create(self, registry: SchemaRegistry) -> SchemaRegistry:
        async with self.session_factory() as session:
            result = await session.execute(
                select(SchemaRegistryModel).where(
                    SchemaRegistryModel.registry_id == registry.registry_id
                )
            )
            existing_model = result.scalar_one_or_none()

            if existing_model:
                existing_model.name = registry.name
                existing_model.url = registry.url
                existing_model.description = registry.description
                existing_model.auth_username = registry.auth_username
                existing_model.auth_password = registry.auth_password
                existing_model.ssl_ca_location = registry.ssl_ca_location
                existing_model.ssl_cert_location = registry.ssl_cert_location
                existing_model.ssl_key_location = registry.ssl_key_location
                existing_model.timeout = registry.timeout
                existing_model.is_active = True
                await session.commit()
                await session.refresh(existing_model)
                logger.info("Schema Registry reactivated: %s", registry.registry_id)
                return self._model_to_domain(existing_model)

            model = SchemaRegistryModel(
                registry_id=registry.registry_id,
                name=registry.name,
                url=registry.url,
                description=registry.description,
                auth_username=registry.auth_username,
                auth_password=registry.auth_password,
                ssl_ca_location=registry.ssl_ca_location,
                ssl_cert_location=registry.ssl_cert_location,
                ssl_key_location=registry.ssl_key_location,
                timeout=registry.timeout,
                is_active=registry.is_active,
            )
            session.add(model)
            await session.commit()
            await session.refresh(model)
            logger.info("Schema Registry created: %s", registry.registry_id)
            return self._model_to_domain(model)

    async def get_by_id(self, registry_id: str) -> SchemaRegistry | None:
        async with self.session_factory() as session:
            result = await session.execute(
                select(SchemaRegistryModel).where(SchemaRegistryModel.registry_id == registry_id)
            )
            model = result.scalar_one_or_none()
            return self._model_to_domain(model) if model else None

    async def list_all(self, active_only: bool = True) -> list[SchemaRegistry]:
        async with self.session_factory() as session:
            query = select(SchemaRegistryModel)
            if active_only:
                query = query.where(SchemaRegistryModel.is_active == True)  # noqa: E712
            result = await session.execute(query.order_by(SchemaRegistryModel.created_at.desc()))
            return [self._model_to_domain(model) for model in result.scalars().all()]

    async def update(self, registry: SchemaRegistry) -> SchemaRegistry:
        async with self.session_factory() as session:
            result = await session.execute(
                select(SchemaRegistryModel).where(
                    SchemaRegistryModel.registry_id == registry.registry_id
                )
            )
            model = result.scalar_one_or_none()
            if not model:
                raise ValueError(f"Schema Registry not found: {registry.registry_id}")

            model.name = registry.name
            model.url = registry.url
            model.description = registry.description
            model.auth_username = registry.auth_username
            model.auth_password = registry.auth_password
            model.ssl_ca_location = registry.ssl_ca_location
            model.ssl_cert_location = registry.ssl_cert_location
            model.ssl_key_location = registry.ssl_key_location
            model.timeout = registry.timeout
            model.is_active = registry.is_active
            await session.commit()
            await session.refresh(model)
            logger.info("Schema Registry updated: %s", registry.registry_id)
            return self._model_to_domain(model)

    async def delete(self, registry_id: str) -> bool:
        async with self.session_factory() as session:
            result = await session.execute(
                select(SchemaRegistryModel).where(SchemaRegistryModel.registry_id == registry_id)
            )
            model = result.scalar_one_or_none()
            if not model:
                return False
            model.is_active = False
            await session.commit()
            logger.info("Schema Registry deleted (soft): %s", registry_id)
            return True

    @staticmethod
    def _model_to_domain(model: SchemaRegistryModel) -> SchemaRegistry:
        return SchemaRegistry(
            registry_id=model.registry_id,
            name=model.name,
            url=model.url,
            description=model.description,
            auth_username=model.auth_username,
            auth_password=model.auth_password,
            ssl_ca_location=model.ssl_ca_location,
            ssl_cert_location=model.ssl_cert_location,
            ssl_key_location=model.ssl_key_location,
            timeout=model.timeout,
            is_active=model.is_active,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
