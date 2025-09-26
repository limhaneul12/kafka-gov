import pytest
from pydantic import ValidationError

from app.topic.interface.schema import (
    PolicyViolation,
    TopicBatchApplyResponse,
    TopicBatchDryRunResponse,
    TopicBatchRequest,
    TopicConfig,
    TopicDetailResponse,
    TopicItem,
    TopicMetadata,
    TopicPlanItem,
    TopicPlanResponse,
)
from app.topic.interface.types import (
    Environment,
    TopicAction,
)

# ------------------------------ TopicMetadata ------------------------------


def test_topic_metadata_valid_and_extra_forbidden():
    m = TopicMetadata(
        owner="team-commerce",
        sla="P99<200ms",
        doc="https://wiki.company.com/streams/orders",
        tags=["pii", "critical"],
    )
    assert m.owner == "team-commerce"

    # extra field should be forbidden
    with pytest.raises(ValidationError):
        TopicMetadata(
            owner="team-commerce",
            tags=["a"],
            extra_field="nope",  # type: ignore[arg-type]
        )

    # tags max length = 10
    with pytest.raises(ValidationError):
        TopicMetadata(owner="team-commerce", tags=[str(i) for i in range(11)])


# -------------------------------- TopicConfig ------------------------------


def test_topic_config_min_insync_not_greater_than_replication():
    # valid
    c = TopicConfig(
        partitions=12,
        replication_factor=3,
        cleanup_policy="delete",
        compression_type="zstd",
        retention_ms=604_800_000,
        min_insync_replicas=2,
        max_message_bytes=1_048_576,
        segment_ms=120_000,
    )
    assert c.replication_factor == 3

    # invalid validator condition
    with pytest.raises(ValidationError):
        TopicConfig(
            partitions=12,
            replication_factor=3,
            min_insync_replicas=5,  # greater than replication_factor
        )

    # strict int: partitions cannot be string
    with pytest.raises(ValidationError):
        TopicConfig(
            partitions="12",  # type: ignore[arg-type]
            replication_factor=3,
        )


# --------------------------------- TopicItem -------------------------------


def test_topic_item_delete_requires_reason_and_no_config():
    # missing reason
    with pytest.raises(ValidationError):
        TopicItem(name="prod.orders.created", action=TopicAction.DELETE)

    # reason present but config provided (should fail)
    with pytest.raises(ValidationError):
        TopicItem(
            name="prod.orders.created",
            action=TopicAction.DELETE,
            reason="cleanup",
            config=TopicConfig(partitions=1, replication_factor=1),
        )

    # valid delete
    ok = TopicItem(name="prod.orders.created", action=TopicAction.DELETE, reason="ok")
    assert ok.reason == "ok"


def test_topic_item_upsert_requires_config_and_metadata():
    # missing config
    with pytest.raises(ValidationError):
        TopicItem(
            name="prod.orders.created",
            action=TopicAction.UPSERT,
            metadata=TopicMetadata(owner="team-commerce"),
        )

    # missing metadata
    with pytest.raises(ValidationError):
        TopicItem(
            name="prod.orders.created",
            action=TopicAction.UPSERT,
            config=TopicConfig(partitions=3, replication_factor=3),
        )

    # valid
    item = TopicItem(
        name="prod.orders.created",
        action=TopicAction.UPSERT,
        config=TopicConfig(partitions=3, replication_factor=3),
        metadata=TopicMetadata(owner="team-commerce"),
    )
    assert item.config.partitions == 3


# ---------------------------- TopicBatchRequest ----------------------------


def test_topic_batch_request_unique_names_and_env_consistency():
    payload = {
        "kind": "TopicBatch",
        "env": Environment.PROD,
        "change_id": "chg-001",
        "items": [
            {
                "name": "prod.orders.created",
                "action": TopicAction.UPSERT,
                "config": {"partitions": 3, "replication_factor": 3},
                "metadata": {"owner": "team-commerce"},
            },
            {
                "name": "prod.orders.created",  # duplicate
                "action": TopicAction.UPSERT,
                "config": {"partitions": 3, "replication_factor": 3},
                "metadata": {"owner": "team-commerce"},
            },
        ],
    }
    with pytest.raises(ValidationError):
        TopicBatchRequest.model_validate(payload)

    # env mismatch between batch and item name
    payload = {
        "kind": "TopicBatch",
        "env": Environment.PROD,
        "change_id": "chg-001",
        "items": [
            {
                "name": "stg.orders.created",  # mismatch with env=prod
                "action": TopicAction.UPSERT,
                "config": {"partitions": 3, "replication_factor": 3},
                "metadata": {"owner": "team-commerce"},
            }
        ],
    }
    with pytest.raises(ValidationError):
        TopicBatchRequest.model_validate(payload)

    # valid minimal
    ok_payload = {
        "env": Environment.PROD,
        "change_id": "chg-002",
        "items": [
            {
                "name": "prod.orders.created",
                "action": TopicAction.UPSERT,
                "config": {"partitions": 3, "replication_factor": 3},
                "metadata": {"owner": "team-commerce"},
            }
        ],
    }
    req = TopicBatchRequest.model_validate(ok_payload)
    assert req.kind == "TopicBatch"


# ------------------------------ TopicPlanItem ------------------------------


def test_topic_plan_item_action_pattern():
    with pytest.raises(ValidationError):
        TopicPlanItem(name="prod.orders.created", action="UNKNOWN")

    tpi = TopicPlanItem(name="prod.orders.created", action="CREATE")
    assert tpi.action == "CREATE"


# ----------------------------- PolicyViolation ----------------------------


def test_policy_violation_defaults_and_patterns():
    pv = PolicyViolation(
        name="prod.tmp.experiment",
        rule="forbid.prefix",
        message="not allowed",
    )
    assert pv.severity == "error"

    # valid warning
    pv_warn = PolicyViolation(
        name="prod.tmp.experiment",
        rule="forbid.prefix",
        message="not allowed",
        severity="warning",
    )
    assert pv_warn.severity == "warning"

    # invalid severity
    with pytest.raises(ValidationError):
        PolicyViolation(
            name="prod.tmp.experiment",
            rule="forbid.prefix",
            message="not allowed",
            severity="warn",  # must be error|warning
        )


# ------------------------------ Response DTOs -----------------------------


def test_topic_responses_models_create():
    # DryRunResponse
    drr = TopicBatchDryRunResponse(
        env=Environment.PROD,
        change_id="chg-id",
        plan=[],
        violations=[],
        summary={"total_items": 0},
    )
    assert drr.summary == {"total_items": 0}

    # ApplyResponse
    ar = TopicBatchApplyResponse(
        env=Environment.PROD,
        change_id="chg-id",
        applied=["prod.orders.created"],
        skipped=[],
        failed=[],
        audit_id="audit-1",
        summary={"applied_count": 1},
    )
    assert ar.applied == ["prod.orders.created"]

    # DetailResponse
    dr = TopicDetailResponse(
        name="prod.orders.created",
        config=TopicConfig(partitions=3, replication_factor=3),
    )
    assert dr.name == "prod.orders.created"

    # PlanResponse
    pr = TopicPlanResponse(
        change_id="chg-id",
        env=Environment.PROD,
        status="applied",
        created_at="2025-09-25T10:00:00Z",
        plan=[],
    )
    assert pr.status == "applied"
