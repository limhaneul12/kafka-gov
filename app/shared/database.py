"""공통 데이터베이스 모듈 - MySQL + SQLAlchemy"""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """SQLAlchemy Base 클래스"""

    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )


class DatabaseManager:
    """데이터베이스 연결 관리자"""

    def __init__(self, database_url: str, echo: bool = False) -> None:
        self.database_url = database_url
        self.echo = echo
        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None

    async def initialize(self) -> None:
        """데이터베이스 연결 초기화"""
        if self._engine is not None:
            return

        self._engine = create_async_engine(
            self.database_url,
            echo=self.echo,
            pool_pre_ping=True,
            pool_recycle=3600,  # 1시간
            pool_size=10,
            max_overflow=20,
            # 성능 최적화 설정
            pool_timeout=30,  # 연결 대기 시간
            pool_reset_on_return="commit",  # 트랜잭션 정리
            connect_args={
                "charset": "utf8mb4",
                "use_unicode": True,
                "autocommit": False,
            },
        )

        self._session_factory = async_sessionmaker(
            bind=self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        logger.info("Database connection initialized")

    async def close(self) -> None:
        """데이터베이스 연결 종료"""
        if self._engine is not None:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None
            logger.info("Database connection closed")

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """데이터베이스 세션 컨텍스트 매니저"""
        if self._session_factory is None:
            raise RuntimeError("Database not initialized. Call initialize() first.")

        session = self._session_factory()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    async def create_tables(self) -> None:
        """테이블 생성"""
        if self._engine is None:
            raise RuntimeError("Database not initialized. Call initialize() first.")

        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables created")

    async def drop_tables(self) -> None:
        """테이블 삭제 (개발/테스트용)"""
        if self._engine is None:
            raise RuntimeError("Database not initialized. Call initialize() first.")

        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            logger.info("Database tables dropped")

    @asynccontextmanager
    async def get_db_session(self) -> AsyncGenerator[AsyncSession, None]:
        """의존성 주입용 데이터베이스 세션 팩토리"""
        await self.initialize()
        async with self.get_session() as session:
            yield session
