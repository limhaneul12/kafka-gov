"""Cluster Infrastructure Repositories - MySQL 구현체"""

from __future__ import annotations

import logging
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cluster.domain.models import (
    KafkaCluster,
    KafkaConnect,
    ObjectStorage,
    SaslMechanism,
    SchemaRegistry,
    SecurityProtocol,
)
from app.cluster.domain.repositories import (
    IKafkaClusterRepository,
    IKafkaConnectRepository,
    IObjectStorageRepository,
    ISchemaRegistryRepository,
)

from .models import (
    KafkaClusterModel,
    KafkaConnectModel,
    ObjectStorageModel,
    SchemaRegistryModel,
)

logger = logging.getLogger(__name__)

SessionFactory = Callable[..., AbstractAsyncContextManager[AsyncSession]]


class MySQLKafkaClusterRepository(IKafkaClusterRepository):
    """MySQL 기반 Kafka 클러스터 리포지토리 (Session Factory 패턴)"""

    def __init__(self, session_factory: SessionFactory) -> None:
        self.session_factory = session_factory

    async def create(self, cluster: KafkaCluster) -> KafkaCluster:
        """클러스터 생성 (또는 재활성화)"""
        async with self.session_factory() as session:
            # 기존 레코드 확인
            result = await session.execute(
                select(KafkaClusterModel).where(KafkaClusterModel.cluster_id == cluster.cluster_id)
            )
            existing_model = result.scalar_one_or_none()

            if existing_model:
                # 재활성화
                existing_model.name = cluster.name
                existing_model.bootstrap_servers = cluster.bootstrap_servers
                existing_model.description = cluster.description
                existing_model.security_protocol = cluster.security_protocol.value
                existing_model.sasl_mechanism = (
                    cluster.sasl_mechanism.value if cluster.sasl_mechanism else None
                )
                existing_model.sasl_username = cluster.sasl_username
                existing_model.sasl_password = cluster.sasl_password
                existing_model.ssl_ca_location = cluster.ssl_ca_location
                existing_model.ssl_cert_location = cluster.ssl_cert_location
                existing_model.ssl_key_location = cluster.ssl_key_location
                existing_model.request_timeout_ms = cluster.request_timeout_ms
                existing_model.socket_timeout_ms = cluster.socket_timeout_ms
                existing_model.is_active = True
                await session.commit()
                await session.refresh(existing_model)
                logger.info(f"Kafka cluster reactivated: {cluster.cluster_id}")
                return self._model_to_domain(existing_model)
            else:
                # 새 레코드 생성
                model = KafkaClusterModel(
                    cluster_id=cluster.cluster_id,
                    name=cluster.name,
                    bootstrap_servers=cluster.bootstrap_servers,
                    description=cluster.description,
                    security_protocol=cluster.security_protocol.value,
                    sasl_mechanism=cluster.sasl_mechanism.value if cluster.sasl_mechanism else None,
                    sasl_username=cluster.sasl_username,
                    sasl_password=cluster.sasl_password,
                    ssl_ca_location=cluster.ssl_ca_location,
                    ssl_cert_location=cluster.ssl_cert_location,
                    ssl_key_location=cluster.ssl_key_location,
                    request_timeout_ms=cluster.request_timeout_ms,
                    socket_timeout_ms=cluster.socket_timeout_ms,
                    is_active=cluster.is_active,
                )

                session.add(model)
                await session.commit()
                await session.refresh(model)

                logger.info(f"Kafka cluster created: {cluster.cluster_id}")
                return self._model_to_domain(model)

    async def get_by_id(self, cluster_id: str) -> KafkaCluster | None:
        """ID로 클러스터 조회"""
        async with self.session_factory() as session:
            result = await session.execute(
                select(KafkaClusterModel).where(KafkaClusterModel.cluster_id == cluster_id)
            )
            model = result.scalar_one_or_none()

            return self._model_to_domain(model) if model else None

    async def list_all(self, active_only: bool = True) -> list[KafkaCluster]:
        """전체 클러스터 목록 조회"""
        async with self.session_factory() as session:
            query = select(KafkaClusterModel)
            if active_only:
                query = query.where(KafkaClusterModel.is_active == True)  # noqa: E712

            result = await session.execute(query.order_by(KafkaClusterModel.created_at.desc()))
            models = result.scalars().all()

            return [self._model_to_domain(model) for model in models]

    async def update(self, cluster: KafkaCluster) -> KafkaCluster:
        """클러스터 정보 수정"""
        async with self.session_factory() as session:
            result = await session.execute(
                select(KafkaClusterModel).where(KafkaClusterModel.cluster_id == cluster.cluster_id)
            )
            model = result.scalar_one_or_none()

            if not model:
                raise ValueError(f"Kafka cluster not found: {cluster.cluster_id}")

            # 필드 업데이트
            model.name = cluster.name
            model.bootstrap_servers = cluster.bootstrap_servers
            model.description = cluster.description
            model.security_protocol = cluster.security_protocol.value
            model.sasl_mechanism = cluster.sasl_mechanism.value if cluster.sasl_mechanism else None
            model.sasl_username = cluster.sasl_username
            model.sasl_password = cluster.sasl_password
            model.ssl_ca_location = cluster.ssl_ca_location
            model.ssl_cert_location = cluster.ssl_cert_location
            model.ssl_key_location = cluster.ssl_key_location
            model.request_timeout_ms = cluster.request_timeout_ms
            model.socket_timeout_ms = cluster.socket_timeout_ms
            model.is_active = cluster.is_active

            await session.commit()
            await session.refresh(model)

            logger.info(f"Kafka cluster updated: {cluster.cluster_id}")
            return self._model_to_domain(model)

    async def delete(self, cluster_id: str) -> bool:
        """클러스터 삭제 (소프트 삭제)"""
        async with self.session_factory() as session:
            result = await session.execute(
                select(KafkaClusterModel).where(KafkaClusterModel.cluster_id == cluster_id)
            )
            model = result.scalar_one_or_none()

            if not model:
                return False

            model.is_active = False
            await session.commit()

            logger.info(f"Kafka cluster deleted (soft): {cluster_id}")
            return True

    @staticmethod
    def _model_to_domain(model: KafkaClusterModel) -> KafkaCluster:
        """SQLAlchemy 모델 → Domain 모델 변환"""
        return KafkaCluster(
            cluster_id=model.cluster_id,
            name=model.name,
            bootstrap_servers=model.bootstrap_servers,
            description=model.description,
            security_protocol=SecurityProtocol(model.security_protocol),
            sasl_mechanism=SaslMechanism(model.sasl_mechanism) if model.sasl_mechanism else None,
            sasl_username=model.sasl_username,
            sasl_password=model.sasl_password,
            ssl_ca_location=model.ssl_ca_location,
            ssl_cert_location=model.ssl_cert_location,
            ssl_key_location=model.ssl_key_location,
            request_timeout_ms=model.request_timeout_ms,
            socket_timeout_ms=model.socket_timeout_ms,
            is_active=model.is_active,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )


class MySQLSchemaRegistryRepository(ISchemaRegistryRepository):
    """MySQL 기반 Schema Registry 리포지토리 (Session Factory 패턴)"""

    def __init__(self, session_factory: SessionFactory) -> None:
        self.session_factory = session_factory

    async def create(self, registry: SchemaRegistry) -> SchemaRegistry:
        """레지스트리 생성 (또는 재활성화)"""
        async with self.session_factory() as session:
            # 기존 레코드 확인 (소프트 삭제된 것 포함)
            result = await session.execute(
                select(SchemaRegistryModel).where(
                    SchemaRegistryModel.registry_id == registry.registry_id
                )
            )
            existing_model = result.scalar_one_or_none()

            if existing_model:
                # 기존 레코드가 있으면 업데이트 (재활성화)
                existing_model.name = registry.name
                existing_model.url = registry.url
                existing_model.description = registry.description
                existing_model.auth_username = registry.auth_username
                existing_model.auth_password = registry.auth_password
                existing_model.ssl_ca_location = registry.ssl_ca_location
                existing_model.ssl_cert_location = registry.ssl_cert_location
                existing_model.ssl_key_location = registry.ssl_key_location
                existing_model.timeout = registry.timeout
                existing_model.is_active = True  # 재활성화
                await session.commit()
                await session.refresh(existing_model)
                logger.info(f"Schema Registry reactivated: {registry.registry_id}")
                return self._model_to_domain(existing_model)
            else:
                # 새 레코드 생성
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

                logger.info(f"Schema Registry created: {registry.registry_id}")
                return self._model_to_domain(model)

    async def get_by_id(self, registry_id: str) -> SchemaRegistry | None:
        """ID로 레지스트리 조회"""
        async with self.session_factory() as session:
            result = await session.execute(
                select(SchemaRegistryModel).where(SchemaRegistryModel.registry_id == registry_id)
            )
            model = result.scalar_one_or_none()

            return self._model_to_domain(model) if model else None

    async def list_all(self, active_only: bool = True) -> list[SchemaRegistry]:
        """전체 레지스트리 목록 조회"""
        async with self.session_factory() as session:
            query = select(SchemaRegistryModel)
            if active_only:
                query = query.where(SchemaRegistryModel.is_active == True)  # noqa: E712

            result = await session.execute(query.order_by(SchemaRegistryModel.created_at.desc()))
            models = result.scalars().all()

            return [self._model_to_domain(model) for model in models]

    async def update(self, registry: SchemaRegistry) -> SchemaRegistry:
        """레지스트리 정보 수정"""
        async with self.session_factory() as session:
            result = await session.execute(
                select(SchemaRegistryModel).where(
                    SchemaRegistryModel.registry_id == registry.registry_id
                )
            )
            model = result.scalar_one_or_none()

            if not model:
                raise ValueError(f"Schema Registry not found: {registry.registry_id}")

            # 필드 업데이트
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

            logger.info(f"Schema Registry updated: {registry.registry_id}")
            return self._model_to_domain(model)

    async def delete(self, registry_id: str) -> bool:
        """레지스트리 삭제 (소프트 삭제)"""
        async with self.session_factory() as session:
            result = await session.execute(
                select(SchemaRegistryModel).where(SchemaRegistryModel.registry_id == registry_id)
            )
            model = result.scalar_one_or_none()

            if not model:
                return False

            model.is_active = False
            await session.commit()

            logger.info(f"Schema Registry deleted (soft): {registry_id}")
            return True

    @staticmethod
    def _model_to_domain(model: SchemaRegistryModel) -> SchemaRegistry:
        """SQLAlchemy 모델 → Domain 모델 변환"""
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


class MySQLObjectStorageRepository(IObjectStorageRepository):
    """MySQL 기반 Object Storage 리포지토리 (Session Factory 패턴)"""

    def __init__(self, session_factory: SessionFactory) -> None:
        self.session_factory = session_factory

    async def create(self, storage: ObjectStorage) -> ObjectStorage:
        """스토리지 생성 (또는 재활성화)"""
        async with self.session_factory() as session:
            # 기존 레코드 확인
            result = await session.execute(
                select(ObjectStorageModel).where(
                    ObjectStorageModel.storage_id == storage.storage_id
                )
            )
            existing_model = result.scalar_one_or_none()

            if existing_model:
                # 재활성화
                existing_model.name = storage.name
                existing_model.endpoint_url = storage.endpoint_url
                existing_model.description = storage.description
                existing_model.access_key = storage.access_key
                existing_model.secret_key = storage.secret_key
                existing_model.bucket_name = storage.bucket_name
                existing_model.region = storage.region
                existing_model.use_ssl = storage.use_ssl
                existing_model.is_active = True
                await session.commit()
                await session.refresh(existing_model)
                logger.info(f"Object Storage reactivated: {storage.storage_id}")
                return self._model_to_domain(existing_model)
            else:
                # 새 레코드 생성
                model = ObjectStorageModel(
                    storage_id=storage.storage_id,
                    name=storage.name,
                    endpoint_url=storage.endpoint_url,
                    description=storage.description,
                    access_key=storage.access_key,
                    secret_key=storage.secret_key,
                    bucket_name=storage.bucket_name,
                    region=storage.region,
                    use_ssl=storage.use_ssl,
                    is_active=storage.is_active,
                )

                session.add(model)
                await session.commit()
                await session.refresh(model)

                logger.info(f"Object Storage created: {storage.storage_id}")
                return self._model_to_domain(model)

    async def get_by_id(self, storage_id: str) -> ObjectStorage | None:
        """ID로 스토리지 조회"""
        async with self.session_factory() as session:
            result = await session.execute(
                select(ObjectStorageModel).where(ObjectStorageModel.storage_id == storage_id)
            )
            model = result.scalar_one_or_none()

            return self._model_to_domain(model) if model else None

    async def list_all(self, active_only: bool = True) -> list[ObjectStorage]:
        """전체 스토리지 목록 조회"""
        async with self.session_factory() as session:
            query = select(ObjectStorageModel)
            if active_only:
                query = query.where(ObjectStorageModel.is_active == True)  # noqa: E712

            result = await session.execute(query.order_by(ObjectStorageModel.created_at.desc()))
            models = result.scalars().all()

            return [self._model_to_domain(model) for model in models]

    async def update(self, storage: ObjectStorage) -> ObjectStorage:
        """스토리지 정보 수정"""
        async with self.session_factory() as session:
            result = await session.execute(
                select(ObjectStorageModel).where(
                    ObjectStorageModel.storage_id == storage.storage_id
                )
            )
            model = result.scalar_one_or_none()

            if not model:
                raise ValueError(f"Object Storage not found: {storage.storage_id}")

            # 필드 업데이트
            model.name = storage.name
            model.endpoint_url = storage.endpoint_url
            model.description = storage.description
            model.access_key = storage.access_key
            model.secret_key = storage.secret_key
            model.bucket_name = storage.bucket_name
            model.region = storage.region
            model.use_ssl = storage.use_ssl
            model.is_active = storage.is_active

            await session.commit()
            await session.refresh(model)

            logger.info(f"Object Storage updated: {storage.storage_id}")
            return self._model_to_domain(model)

    async def delete(self, storage_id: str) -> bool:
        """스토리지 삭제 (소프트 삭제)"""
        async with self.session_factory() as session:
            result = await session.execute(
                select(ObjectStorageModel).where(ObjectStorageModel.storage_id == storage_id)
            )
            model = result.scalar_one_or_none()

            if not model:
                return False

            model.is_active = False
            await session.commit()

            logger.info(f"Object Storage deleted (soft): {storage_id}")
            return True

    @staticmethod
    def _model_to_domain(model: ObjectStorageModel) -> ObjectStorage:
        """SQLAlchemy 모델 → Domain 모델 변환"""
        return ObjectStorage(
            storage_id=model.storage_id,
            name=model.name,
            endpoint_url=model.endpoint_url,
            description=model.description,
            access_key=model.access_key,
            secret_key=model.secret_key,
            bucket_name=model.bucket_name,
            region=model.region,
            use_ssl=model.use_ssl,
            is_active=model.is_active,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )


class MySQLKafkaConnectRepository(IKafkaConnectRepository):
    """MySQL 기반 Kafka Connect 리포지토리 (Session Factory 패턴)"""

    def __init__(self, session_factory: SessionFactory) -> None:
        self.session_factory = session_factory

    async def create(self, connect: KafkaConnect) -> KafkaConnect:
        """Connect 생성 (또는 재활성화)"""
        async with self.session_factory() as session:
            # 기존 레코드 확인
            result = await session.execute(
                select(KafkaConnectModel).where(KafkaConnectModel.connect_id == connect.connect_id)
            )
            existing_model = result.scalar_one_or_none()

            if existing_model:
                # 재활성화
                existing_model.cluster_id = connect.cluster_id
                existing_model.name = connect.name
                existing_model.url = connect.url
                existing_model.description = connect.description
                existing_model.auth_username = connect.auth_username
                existing_model.auth_password = connect.auth_password
                existing_model.is_active = True
                await session.commit()
                await session.refresh(existing_model)
                logger.info(f"Kafka Connect reactivated: {connect.connect_id}")
                return self._model_to_domain(existing_model)
            else:
                # 새 레코드 생성
                model = KafkaConnectModel(
                    connect_id=connect.connect_id,
                    cluster_id=connect.cluster_id,
                    name=connect.name,
                    url=connect.url,
                    description=connect.description,
                    auth_username=connect.auth_username,
                    auth_password=connect.auth_password,
                    is_active=connect.is_active,
                )

                session.add(model)
                await session.commit()
                await session.refresh(model)

                logger.info(f"Kafka Connect created: {connect.connect_id}")
                return self._model_to_domain(model)

    async def get_by_id(self, connect_id: str) -> KafkaConnect | None:
        """ID로 Connect 조회"""
        async with self.session_factory() as session:
            result = await session.execute(
                select(KafkaConnectModel).where(KafkaConnectModel.connect_id == connect_id)
            )
            model = result.scalar_one_or_none()

            return self._model_to_domain(model) if model else None

    async def list_by_cluster(self, cluster_id: str) -> list[KafkaConnect]:
        """클러스터별 Connect 목록 조회"""
        async with self.session_factory() as session:
            result = await session.execute(
                select(KafkaConnectModel)
                .where(KafkaConnectModel.cluster_id == cluster_id)
                .where(KafkaConnectModel.is_active == True)  # noqa: E712
                .order_by(KafkaConnectModel.created_at.desc())
            )
            models = result.scalars().all()

            return [self._model_to_domain(model) for model in models]

    async def list_all(self, active_only: bool = True) -> list[KafkaConnect]:
        """전체 Connect 목록 조회"""
        async with self.session_factory() as session:
            query = select(KafkaConnectModel)
            if active_only:
                query = query.where(KafkaConnectModel.is_active == True)  # noqa: E712
            query = query.order_by(KafkaConnectModel.created_at.desc())

            result = await session.execute(query)
            models = result.scalars().all()

            return [self._model_to_domain(model) for model in models]

    async def update(self, connect: KafkaConnect) -> KafkaConnect:
        """Connect 정보 수정"""
        async with self.session_factory() as session:
            result = await session.execute(
                select(KafkaConnectModel).where(KafkaConnectModel.connect_id == connect.connect_id)
            )
            model = result.scalar_one_or_none()

            if not model:
                raise ValueError(f"Kafka Connect not found: {connect.connect_id}")

            # 필드 업데이트
            model.cluster_id = connect.cluster_id
            model.name = connect.name
            model.url = connect.url
            model.description = connect.description
            model.auth_username = connect.auth_username
            model.auth_password = connect.auth_password
            model.is_active = connect.is_active

            await session.commit()
            await session.refresh(model)

            logger.info(f"Kafka Connect updated: {connect.connect_id}")
            return self._model_to_domain(model)

    async def delete(self, connect_id: str) -> bool:
        """Connect 삭제 (소프트 삭제)"""
        async with self.session_factory() as session:
            result = await session.execute(
                select(KafkaConnectModel).where(KafkaConnectModel.connect_id == connect_id)
            )
            model = result.scalar_one_or_none()

            if not model:
                return False

            model.is_active = False
            await session.commit()

            logger.info(f"Kafka Connect deleted (soft): {connect_id}")
            return True

    @staticmethod
    def _model_to_domain(model: KafkaConnectModel) -> KafkaConnect:
        """SQLAlchemy 모델 → Domain 모델 변환"""
        return KafkaConnect(
            connect_id=model.connect_id,
            cluster_id=model.cluster_id,
            name=model.name,
            url=model.url,
            description=model.description,
            auth_username=model.auth_username,
            auth_password=model.auth_password,
            is_active=model.is_active,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
