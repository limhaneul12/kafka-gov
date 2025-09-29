"""MySQLTopicMetadataRepository 메타 정보/메타데이터 브랜치 커버리지 보강"""

from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.topic.infrastructure.repository.mysql_repository import MySQLTopicMetadataRepository


@pytest.fixture
def mock_session() -> AsyncMock:
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def repository(mock_session: AsyncMock) -> MySQLTopicMetadataRepository:
    return MySQLTopicMetadataRepository(mock_session)


@pytest.mark.asyncio
async def test_get_plan_meta_with_apply(
    repository: MySQLTopicMetadataRepository, mock_session: AsyncMock
) -> None:
    """get_plan_meta가 상태/생성시각/적용시각을 반환해야 한다."""
    change_id = "chg-1"
    plan_model = SimpleNamespace(status="pending", created_at=_dt("2025-09-27T00:00:00"))
    apply_model = SimpleNamespace(applied_at=_dt("2025-09-27T01:00:00"))

    # 첫 execute -> TopicPlanModel
    first_result = MagicMock()
    first_result.scalar_one_or_none.return_value = plan_model
    # 두번째 execute -> TopicApplyResultModel
    second_result = MagicMock()
    second_result.scalar_one_or_none.return_value = apply_model

    mock_session.execute.side_effect = [first_result, second_result]

    meta = await repository.get_plan_meta(change_id)
    assert meta is not None
    assert meta["status"] == "pending"
    assert meta["created_at"].startswith("2025-09-27")
    assert meta["applied_at"].startswith("2025-09-27T01")


@pytest.mark.asyncio
async def test_get_plan_meta_without_apply(
    repository: MySQLTopicMetadataRepository, mock_session: AsyncMock
) -> None:
    """적용 결과가 없으면 applied_at은 None이어야 한다."""
    change_id = "chg-2"
    plan_model = SimpleNamespace(status="applied", created_at=_dt("2025-09-27T00:00:00"))

    first_result = MagicMock()
    first_result.scalar_one_or_none.return_value = plan_model
    second_result = MagicMock()
    second_result.scalar_one_or_none.return_value = None

    mock_session.execute.side_effect = [first_result, second_result]

    meta = await repository.get_plan_meta(change_id)
    assert meta is not None
    assert meta["status"] == "applied"
    assert meta["applied_at"] is None


@pytest.mark.asyncio
async def test_save_topic_metadata_update_existing(
    repository: MySQLTopicMetadataRepository, mock_session: AsyncMock
) -> None:
    """기존 레코드가 있으면 필드를 갱신하고 merge 호출해야 한다."""
    topic_name = "dev.user.events"
    metadata = {
        "owner": "data-team",
        "sla": "99.9%",
        "doc": None,
        "tags": ["critical"],
        "config": {},
    }

    existing = SimpleNamespace(
        owner=None, sla=None, doc=None, tags=None, config=None, updated_by=None
    )
    first_result = MagicMock()
    first_result.scalar_one_or_none.return_value = existing
    mock_session.execute.return_value = first_result

    await repository.save_topic_metadata(topic_name, metadata)

    # 필드 업데이트 되었는지
    assert existing.owner == "data-team"
    assert existing.sla == "99.9%"
    assert existing.tags == ["critical"]
    mock_session.merge.assert_called_once()
    mock_session.flush.assert_called_once()


@pytest.mark.asyncio
async def test_save_topic_metadata_create_new(
    repository: MySQLTopicMetadataRepository, mock_session: AsyncMock
) -> None:
    """기존 레코드가 없으면 신규 모델을 생성하여 merge 해야 한다."""
    topic_name = "dev.user.events"
    metadata = {"owner": "data-team"}

    first_result = MagicMock()
    first_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = first_result

    await repository.save_topic_metadata(topic_name, metadata)

    mock_session.merge.assert_called_once()
    mock_session.flush.assert_called_once()


# helpers
def _dt(s: str) -> datetime:
    # allow both naive and Z ISO strings
    s = s.rstrip("Z")
    return datetime.fromisoformat(s)


@pytest.mark.asyncio
async def test_get_plan_with_violations(
    repository: MySQLTopicMetadataRepository, mock_session: AsyncMock
) -> None:
    """get_plan이 violations를 역직렬화해야 한다."""
    change_id = "chg-3"
    plan_model = SimpleNamespace(
        plan_data={
            "change_id": change_id,
            "env": "dev",
            "items": [
                {
                    "name": "dev.user.events",
                    "action": "CREATE",
                    "diff": {"status": "new→created"},
                    "current_config": None,
                    "target_config": {"partitions": "3"},
                }
            ],
            "violations": [
                {
                    "resource_name": "dev.user.events",
                    "rule_id": "partition_rule",
                    "message": "too few partitions",
                    "severity": "error",
                    "field": "partitions",
                }
            ],
        }
    )
    result = MagicMock()
    result.scalar_one_or_none.return_value = plan_model
    mock_session.execute.return_value = result

    plan = await repository.get_plan(change_id)
    assert plan is not None
    assert len(plan.violations) == 1
    assert plan.violations[0].message.startswith("too few")
