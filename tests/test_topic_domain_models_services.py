from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pytest

from app.topic.domain.models.config import DomainTopicConfig, DomainTopicMetadata
from app.topic.domain.models.plan import (
    DomainTopicApplyResult,
    DomainTopicPlan,
    DomainTopicPlanItem,
)
from app.topic.domain.models.report import (
    DryRunItemReport,
    DryRunReport,
    DryRunSummary,
    ViolationDetail,
)
from app.topic.domain.models.spec_batch import DomainTopicBatch, DomainTopicSpec
from app.topic.domain.models.types_enum import (
    DomainCleanupPolicy,
    DomainEnvironment,
    DomainPlanAction,
    DomainTopicAction,
)
from app.topic.domain.repositories.interfaces import ITopicRepository
from app.topic.domain.services import TopicDiffService, TopicPlannerService
from app.topic.domain.utils import (
    calculate_dict_diff,
    format_diff_string,
    merge_configs,
    validate_partition_change,
    validate_replication_factor_change,
)


class FakeTopicRepository(ITopicRepository):
    def __init__(self, current: Mapping[str, dict[str, Any]]) -> None:
        self._current: dict[str, dict[str, Any]] = dict(current)

    async def list_topics(self) -> list[str]:
        return list(self._current.keys())

    async def get_topic_metadata(self, name: str) -> dict[str, Any] | None:
        return None

    async def create_topics(self, specs: list[DomainTopicSpec]) -> dict[str, Exception | None]:
        return {spec.name: None for spec in specs}

    async def delete_topics(self, names: list[str]) -> dict[str, Exception | None]:
        return dict.fromkeys(names)

    async def alter_topic_configs(
        self, configs: dict[str, dict[str, str]]
    ) -> dict[str, Exception | None]:
        return dict.fromkeys(configs)

    async def create_partitions(self, partitions: dict[str, int]) -> dict[str, Exception | None]:
        return dict.fromkeys(partitions)

    async def describe_topics(self, names: list[str]) -> dict[str, dict[str, Any]]:
        return {name: self._current[name] for name in names if name in self._current}


def _topic_config(
    *,
    partitions: int = 3,
    replication_factor: int = 2,
    cleanup_policy: DomainCleanupPolicy = DomainCleanupPolicy.DELETE,
    retention_ms: int | None = 3600000,
    min_insync_replicas: int | None = 1,
    max_message_bytes: int | None = 1000000,
    segment_ms: int | None = 300000,
) -> DomainTopicConfig:
    return DomainTopicConfig(
        partitions=partitions,
        replication_factor=replication_factor,
        cleanup_policy=cleanup_policy,
        retention_ms=retention_ms,
        min_insync_replicas=min_insync_replicas,
        max_message_bytes=max_message_bytes,
        segment_ms=segment_ms,
    )


def _topic_metadata() -> DomainTopicMetadata:
    return DomainTopicMetadata(
        owners=("team-data",),
        doc="https://wiki/topic",
        tags=("core", "orders"),
    )


def _topic_spec(name: str, action: DomainTopicAction = DomainTopicAction.CREATE) -> DomainTopicSpec:
    if action == DomainTopicAction.DELETE:
        return DomainTopicSpec(name=name, action=action)
    return DomainTopicSpec(
        name=name, action=action, config=_topic_config(), metadata=_topic_metadata()
    )


def test_topic_config_validation_and_kafka_config_rendering() -> None:
    with pytest.raises(ValueError):
        DomainTopicConfig(partitions=0, replication_factor=1)

    with pytest.raises(ValueError):
        DomainTopicConfig(partitions=1, replication_factor=0)

    with pytest.raises(ValueError):
        DomainTopicConfig(partitions=1, replication_factor=1, min_insync_replicas=2)

    cfg = _topic_config()
    kafka = cfg.to_kafka_config()
    assert kafka["cleanup.policy"] == "delete"
    assert kafka["retention.ms"] == "3600000"
    assert kafka["min.insync.replicas"] == "1"
    assert kafka["max.message.bytes"] == "1000000"
    assert kafka["segment.ms"] == "300000"


def test_topic_spec_and_batch_validation_and_fingerprint() -> None:
    with pytest.raises(ValueError):
        DomainTopicSpec(
            name="",
            action=DomainTopicAction.CREATE,
            config=_topic_config(),
            metadata=_topic_metadata(),
        )

    with pytest.raises(ValueError):
        DomainTopicSpec(name="dev.a", action=DomainTopicAction.CREATE, metadata=_topic_metadata())

    with pytest.raises(ValueError):
        DomainTopicSpec(name="dev.a", action=DomainTopicAction.CREATE, config=_topic_config())

    with pytest.raises(ValueError):
        DomainTopicSpec(name="dev.a", action=DomainTopicAction.DELETE, config=_topic_config())

    spec = _topic_spec("dev.orders")
    assert spec.environment == DomainEnvironment.DEV
    assert len(spec.fingerprint()) == 16

    unknown_env_spec = _topic_spec("foo.orders")
    assert unknown_env_spec.environment == DomainEnvironment.DEV

    with pytest.raises(ValueError):
        DomainTopicBatch(change_id="", env=DomainEnvironment.DEV, specs=(spec,))

    with pytest.raises(ValueError):
        DomainTopicBatch(change_id="chg", env=DomainEnvironment.DEV, specs=())

    with pytest.raises(ValueError):
        DomainTopicBatch(change_id="chg", env=DomainEnvironment.DEV, specs=(spec, spec))

    batch = DomainTopicBatch(change_id="chg", env=DomainEnvironment.DEV, specs=(spec,))
    assert len(batch.fingerprint()) == 16


def test_topic_plan_and_apply_result_helpers() -> None:
    item_create = DomainTopicPlanItem(
        name="dev.a", action=DomainPlanAction.CREATE, diff={"status": "new"}
    )
    item_alter = DomainTopicPlanItem(name="dev.b", action=DomainPlanAction.ALTER, diff={"a": "1→2"})
    item_delete = DomainTopicPlanItem(
        name="dev.c", action=DomainPlanAction.DELETE, diff={"status": "exists→deleted"}
    )

    with pytest.raises(ValueError):
        DomainTopicPlanItem(name="", action=DomainPlanAction.CREATE, diff={})

    with pytest.raises(ValueError):
        DomainTopicPlan(
            change_id="", env=DomainEnvironment.DEV, items=(item_create,), violations=()
        )

    plan = DomainTopicPlan(
        change_id="chg",
        env=DomainEnvironment.DEV,
        items=(item_create, item_alter, item_delete),
        violations=(),
    )
    assert plan.has_violations is False
    assert plan.can_apply is True
    assert plan.summary()["create_count"] == 1
    assert plan.summary()["alter_count"] == 1
    assert plan.summary()["delete_count"] == 1

    with pytest.raises(ValueError):
        DomainTopicApplyResult(
            change_id="",
            env=DomainEnvironment.DEV,
            applied=("dev.a",),
            skipped=(),
            failed=(),
            audit_id="a1",
        )

    with pytest.raises(ValueError):
        DomainTopicApplyResult(
            change_id="chg",
            env=DomainEnvironment.DEV,
            applied=("dev.a",),
            skipped=(),
            failed=(),
            audit_id="",
        )

    result = DomainTopicApplyResult(
        change_id="chg",
        env=DomainEnvironment.DEV,
        applied=("dev.a",),
        skipped=("dev.b",),
        failed=({"name": "dev.c"},),
        audit_id="audit-1",
    )
    assert result.summary() == {
        "total_items": 3,
        "planned_count": 2,
        "applied_count": 1,
        "skipped_count": 1,
        "failed_count": 1,
        "warning_count": 0,
    }


def test_topic_utils_cover_branches() -> None:
    diff = calculate_dict_diff({"a": 1, "b": 2}, {"a": 1, "b": 3, "c": 4})
    assert diff == {"b": (2, 3), "c": (None, 4)}

    assert format_diff_string(None, "x") == "none→x"
    assert format_diff_string("x", None) == "x→none"

    base_obj: dict[str, object] = {"a": "1", "b": "2"}
    override_obj: dict[str, object] = {"b": None, "c": "3"}
    merged = merge_configs(base_obj, override_obj)
    assert merged == {"a": "1", "b": "2", "c": "3"}

    assert validate_partition_change(3, 3) is True
    assert validate_partition_change(3, 5) is True
    assert validate_partition_change(5, 3) is False

    assert validate_replication_factor_change(3, 3) == (True, None)
    ok, msg = validate_replication_factor_change(2, 3)
    assert ok is False
    assert msg is not None and "Cannot change replication factor" in msg


@pytest.mark.asyncio
async def test_topic_planner_service_create_delete_alter_skip_paths() -> None:
    current_topics = {
        "dev.keep": {
            "partition_count": 3,
            "replication_factor": 2,
            "config": {
                "cleanup.policy": "delete",
                "retention.ms": "3600000",
                "min.insync.replicas": "1",
            },
        },
        "dev.delete": {
            "partition_count": 1,
            "replication_factor": 1,
            "config": {},
        },
    }
    service = TopicPlannerService(FakeTopicRepository(current_topics))

    specs = (
        _topic_spec("dev.new"),
        _topic_spec("dev.keep", action=DomainTopicAction.UPDATE),
        _topic_spec("dev.delete", action=DomainTopicAction.DELETE),
        _topic_spec("dev.missing-delete", action=DomainTopicAction.DELETE),
    )
    batch = DomainTopicBatch(change_id="chg1", env=DomainEnvironment.DEV, specs=specs)

    plan = await service.create_plan(batch, actor="tester")
    assert plan.change_id == "chg1"
    assert len(plan.items) == 3
    actions = {item.name: item.action for item in plan.items}
    assert actions["dev.new"] == DomainPlanAction.CREATE
    assert actions["dev.keep"] == DomainPlanAction.ALTER
    assert actions["dev.delete"] == DomainPlanAction.DELETE


def test_topic_planner_no_diff_returns_none_on_plan_item() -> None:
    service = TopicPlannerService(FakeTopicRepository({}))
    spec = _topic_spec("dev.same", action=DomainTopicAction.UPDATE)
    current = {
        "partition_count": 3,
        "replication_factor": 2,
        "config": spec.config.to_kafka_config() if spec.config else {},
    }
    item = service._create_plan_item(spec, current)
    assert item is None


def test_topic_diff_service_paths() -> None:
    current = _topic_config(partitions=3, replication_factor=2)
    target = _topic_config(partitions=5, replication_factor=2, retention_ms=7200000)

    assert TopicDiffService.compare_configs(None, None) == {}
    created = TopicDiffService.compare_configs(None, target)
    assert created is not None and created["partitions"] == (None, 5)

    deleted = TopicDiffService.compare_configs(current, None)
    assert deleted is not None and deleted["replication_factor"] == (2, None)

    changed = TopicDiffService.compare_configs(current, target)
    assert changed is not None and changed["partitions"] == (3, 5)

    assert TopicDiffService.is_partition_increase_only(3, 4) is True
    assert TopicDiffService.is_partition_increase_only(4, 3) is False

    assert TopicDiffService.validate_config_changes(None, target) == []
    assert TopicDiffService.validate_config_changes(current, None) == []

    errors = TopicDiffService.validate_config_changes(
        _topic_config(partitions=4, replication_factor=2),
        _topic_config(partitions=2, replication_factor=3),
    )
    assert len(errors) == 2
    assert "Cannot decrease partitions" in errors[0]
    assert "Cannot change replication factor" in errors[1]


def test_dry_run_report_to_dict() -> None:
    violation = ViolationDetail(
        target="dev.orders", policy_type="naming", message="bad", level="error"
    )
    item = DryRunItemReport(
        name="dev.orders", action="create", diff={"a": "b"}, violations=(violation,)
    )
    report = DryRunReport(
        change_id="chg1",
        env="dev",
        summary=DryRunSummary(
            total_items=1, total_violations=1, error_violations=1, can_apply=False
        ),
        items=(item,),
        violations=(violation,),
    )

    payload = report.to_dict()
    assert payload["change_id"] == "chg1"
    assert payload["summary"]["can_apply"] is False
    assert payload["items"][0]["violations"][0]["policy_type"] == "naming"
