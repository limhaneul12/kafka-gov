"""TopicBatchApplyUseCase 업데이트 경로 커버리지 보강"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.topic.application.use_cases import TopicBatchApplyUseCase
from app.topic.domain.models import (
    DomainEnvironment,
    DomainTopicAction,
    DomainTopicBatch,
    DomainTopicConfig,
    DomainTopicMetadata,
    DomainTopicSpec,
)
from app.topic.domain.repositories.interfaces import (
    IAuditRepository,
    ITopicMetadataRepository,
    ITopicRepository,
)


@pytest.fixture
def mock_topic_repository() -> AsyncMock:
    return AsyncMock(spec=ITopicRepository)


@pytest.fixture
def mock_metadata_repository() -> AsyncMock:
    return AsyncMock(spec=ITopicMetadataRepository)


@pytest.fixture
def mock_audit_repository() -> AsyncMock:
    return AsyncMock(spec=IAuditRepository)


def _make_update_spec() -> DomainTopicSpec:
    return DomainTopicSpec(
        name="dev.update.topic",
        action=DomainTopicAction.UPDATE,
        config=DomainTopicConfig(partitions=6, replication_factor=2, retention_ms=86400000),
        metadata=DomainTopicMetadata(owner="data-team"),
    )


@pytest.mark.asyncio
async def test_update_flow_success(
    mock_topic_repository: AsyncMock,
    mock_metadata_repository: AsyncMock,
    mock_audit_repository: AsyncMock,
) -> None:
    """UPDATE: 파티션 증가 + 설정 변경이 모두 성공하면 applied에 포함된다."""
    spec = _make_update_spec()
    batch = DomainTopicBatch(change_id="chg-u1", env=DomainEnvironment.DEV, specs=(spec,))

    mock_topic_repository.describe_topics.return_value = {
        spec.name: {"partition_count": 3, "config": {"retention.ms": "1000"}}
    }
    mock_topic_repository.create_partitions.return_value = {spec.name: None}
    mock_topic_repository.alter_topic_configs.return_value = {spec.name: None}

    use_case = TopicBatchApplyUseCase(
        topic_repository=mock_topic_repository,
        metadata_repository=mock_metadata_repository,
        audit_repository=mock_audit_repository,
        policy_adapter=AsyncMock(),
    )

    result = await use_case.execute(batch, actor="tester")

    assert spec.name in result.applied
    assert len(result.failed) == 0


@pytest.mark.asyncio
async def test_update_flow_partition_failure(
    mock_topic_repository: AsyncMock,
    mock_metadata_repository: AsyncMock,
    mock_audit_repository: AsyncMock,
) -> None:
    """UPDATE: 파티션 증가 실패 시 failed에 기록되고, ALTER_CONFIG 성공이어도 applied에는 포함되지 않는다."""
    spec = _make_update_spec()
    batch = DomainTopicBatch(change_id="chg-u2", env=DomainEnvironment.DEV, specs=(spec,))

    mock_topic_repository.describe_topics.return_value = {spec.name: {"partition_count": 3}}
    mock_topic_repository.create_partitions.return_value = {spec.name: Exception("partition fail")}
    mock_topic_repository.alter_topic_configs.return_value = {spec.name: None}

    use_case = TopicBatchApplyUseCase(
        topic_repository=mock_topic_repository,
        metadata_repository=mock_metadata_repository,
        audit_repository=mock_audit_repository,
        policy_adapter=AsyncMock(),
    )

    result = await use_case.execute(batch, actor="tester")

    assert spec.name not in result.applied
    assert any(f["action"] == "ALTER_PARTITIONS" for f in result.failed)


@pytest.mark.asyncio
async def test_update_flow_config_failure_without_partition_increase(
    mock_topic_repository: AsyncMock,
    mock_metadata_repository: AsyncMock,
    mock_audit_repository: AsyncMock,
) -> None:
    """UPDATE: 파티션 증가가 필요 없고 ALTER_CONFIG 실패 시 failed에 누적된다."""
    spec = _make_update_spec()
    # 현재 파티션 수가 목표와 동일하여 partition_changes 비어야 함
    mock_topic_repository.describe_topics.return_value = {
        spec.name: {"partition_count": 6, "config": {}}
    }
    mock_topic_repository.create_partitions.return_value = {}
    mock_topic_repository.alter_topic_configs.return_value = {spec.name: Exception("config fail")}

    batch = DomainTopicBatch(change_id="chg-u3", env=DomainEnvironment.DEV, specs=(spec,))

    use_case = TopicBatchApplyUseCase(
        topic_repository=mock_topic_repository,
        metadata_repository=mock_metadata_repository,
        audit_repository=mock_audit_repository,
        policy_adapter=AsyncMock(),
    )

    result = await use_case.execute(batch, actor="tester")

    assert any(f["action"] == "ALTER_CONFIG" for f in result.failed)
    assert spec.name not in result.applied


@pytest.mark.asyncio
async def test_delete_flow_failure(
    mock_topic_repository: AsyncMock,
    mock_metadata_repository: AsyncMock,
    mock_audit_repository: AsyncMock,
) -> None:
    """DELETE: 삭제 실패 시 failed에 기록되어야 한다."""
    spec = DomainTopicSpec(
        name="dev.deprecated.topic", action=DomainTopicAction.DELETE, reason="cleanup"
    )
    batch = DomainTopicBatch(change_id="chg-d1", env=DomainEnvironment.DEV, specs=(spec,))

    mock_topic_repository.create_topics.return_value = {}
    mock_topic_repository.describe_topics.return_value = {}
    mock_topic_repository.delete_topics.return_value = {spec.name: Exception("not found")}

    use_case = TopicBatchApplyUseCase(
        topic_repository=mock_topic_repository,
        metadata_repository=mock_metadata_repository,
        audit_repository=mock_audit_repository,
        policy_adapter=AsyncMock(),
    )

    result = await use_case.execute(batch, actor="tester")

    assert any(f["name"] == spec.name and f["action"] == "DELETE" for f in result.failed)
