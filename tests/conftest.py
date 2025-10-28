"""pytest 공통 설정 및 픽스처"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.shared.database import Base


@pytest.fixture(scope="session")
def event_loop_policy():
    """이벤트 루프 정책 설정"""
    return asyncio.DefaultEventLoopPolicy()


@pytest.fixture(scope="session")
def event_loop(event_loop_policy):
    """세션 스코프 이벤트 루프"""
    loop = event_loop_policy.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_engine() -> AsyncGenerator[AsyncEngine, None]:
    """테스트용 SQLite 엔진 (세션 스코프)"""
    # 메모리 DB 사용
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
    )

    # 테이블 생성
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # 정리
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(test_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """테스트용 데이터베이스 세션 (함수 스코프)"""
    # 테스트 전: 모든 테이블 데이터 삭제
    async with test_engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())

    session_factory = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with session_factory() as session:
        yield session
        # 각 테스트는 자체적으로 commit하므로 여기서는 아무것도 하지 않음

    # 테스트 후: 모든 테이블 데이터 삭제
    async with test_engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())


@pytest_asyncio.fixture(scope="function")
async def clean_db(test_engine: AsyncEngine) -> AsyncGenerator[None, None]:
    """각 테스트 전후로 DB 클린업"""
    # 테스트 전: 모든 테이블 데이터 삭제
    async with test_engine.begin() as conn:
        # SQLite는 TRUNCATE를 지원하지 않으므로 DELETE 사용
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())

    yield

    # 테스트 후: 모든 테이블 데이터 삭제
    async with test_engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())


@pytest.fixture
def mock_kafka_config() -> dict[str, Any]:
    """Mock Kafka 설정"""
    return {
        "bootstrap.servers": "localhost:9092",
        "security.protocol": "PLAINTEXT",
        "request.timeout.ms": 30000,
        "retries": 3,
    }


@pytest.fixture
def mock_schema_registry_config() -> dict[str, Any]:
    """Mock Schema Registry 설정"""
    return {
        "url": "http://localhost:8081",
        "timeout": 30,
    }


@pytest.fixture
def sample_topic_name() -> str:
    """샘플 토픽 이름"""
    return "test-topic"


@pytest.fixture
def sample_schema_json() -> dict[str, Any]:
    """샘플 Avro 스키마"""
    return {
        "type": "record",
        "name": "TestRecord",
        "namespace": "com.example",
        "fields": [
            {"name": "id", "type": "string"},
            {"name": "value", "type": "int"},
            {"name": "timestamp", "type": "long"},
        ],
    }
