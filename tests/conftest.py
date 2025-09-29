"""pytest 공통 설정 및 픽스처 정의."""

import asyncio
import tempfile
from collections.abc import AsyncGenerator
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import pytest_asyncio
from confluent_kafka.admin import AdminClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.shared.container import infrastructure_container
from app.shared.database import Base, db_manager, initialize_database


@pytest.fixture(scope="session")
def event_loop():
    """세션 스코프 이벤트 루프 생성."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_db_engine():
    """테스트용 SQLite 비동기 엔진 생성."""
    # 임시 파일로 SQLite DB 생성
    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as temp_db:
        temp_db_path = temp_db.name

    database_url = f"sqlite+aiosqlite:///{temp_db_path}"
    engine = create_async_engine(
        database_url,
        echo=False,  # 테스트 시 SQL 로그 비활성화
        future=True,
    )

    # 테이블 생성
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # FastAPI 의존성(get_db_session)에서 사용할 전역 DatabaseManager 초기화
    # 동일한 SQLite URL을 사용하여 라우터 의존성 충족
    initialize_database(database_url)
    # db_manager는 initialize_database 호출 이후 설정됨
    if db_manager is not None:
        await db_manager.initialize()
        await db_manager.create_tables()

    # Kafka AdminClient DI 주입 (테스트용 Stub)
    infrastructure_container.kafka_admin_client.override(MagicMock(spec=AdminClient))

    yield engine

    # 정리
    await engine.dispose()
    Path(temp_db_path).unlink(missing_ok=True)


@pytest_asyncio.fixture
async def test_db_session(test_db_engine) -> AsyncGenerator[AsyncSession, None]:
    """테스트용 데이터베이스 세션 생성."""
    async_session = sessionmaker(test_db_engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        yield session
        await session.rollback()  # 각 테스트 후 롤백


# FastAPI 라우터 의존성(get_db_session)을 위한 전역 DB 초기화 보장
@pytest_asyncio.fixture(scope="session", autouse=True)
async def _ensure_global_db_initialized(test_db_engine) -> None:
    """세션 시작 시 전역 DatabaseManager 초기화 보장."""
    # test_db_engine 픽스처 호출만으로 initialize_database + create_tables가 수행됨
    # 별도 동작은 필요 없음
    return None


@pytest.fixture
def temp_dir():
    """임시 디렉토리 생성."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)
