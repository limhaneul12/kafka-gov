import pytest
from pydantic import BaseModel, ValidationError

from app.topic.interface.types.type_hints import (
    ChangeId,
    DocumentUrl,
    MaxMessageBytes,
    MinInsyncReplicas,
    PartitionCount,
    PlanStatus,
    ReplicationFactor,
    RetentionMs,
    SegmentMs,
    SlaRequirement,
    TagName,
    TeamName,
    TopicName,
)


class StringTypesModel(BaseModel):
    topic: TopicName
    change: ChangeId
    team: TeamName
    doc: DocumentUrl
    sla: SlaRequirement
    tag: TagName
    status: PlanStatus


class IntTypesModel(BaseModel):
    partitions: PartitionCount
    replication_factor: ReplicationFactor
    retention_ms: RetentionMs
    min_insync_replicas: MinInsyncReplicas
    segment_ms: SegmentMs
    max_message_bytes: MaxMessageBytes


def test_topic_name_valid_and_invalid():
    # valid
    m = StringTypesModel(
        topic="prod.orders.created",
        change="chg_001",
        team="team-commerce",
        doc="https://wiki.company.com/streams/orders",
        sla="P99<200ms",
        tag="critical",
        status="pending",
    )
    assert m.topic == "prod.orders.created"

    # invalid: missing env prefix
    with pytest.raises(ValidationError):
        StringTypesModel(
            topic="orders.created",
            change="chg_001",
            team="team-commerce",
            doc="https://wiki.company.com/streams/orders",
            sla="P99<200ms",
            tag="critical",
            status="pending",
        )

    # invalid: uppercase letter not allowed by pattern
    with pytest.raises(ValidationError):
        StringTypesModel(
            topic="PROD.orders.created",
            change="chg_001",
            team="team-commerce",
            doc="https://wiki.company.com/streams/orders",
            sla="P99<200ms",
            tag="critical",
            status="pending",
        )


def test_change_id_and_teamname_patterns():
    # ChangeId invalid char (space)
    with pytest.raises(ValidationError):
        StringTypesModel(
            topic="prod.orders.created",
            change="chg 001",
            team="team-commerce",
            doc="https://wiki",
            sla="x",
            tag="ok",
            status="pending",
        )

    # TeamName uppercase invalid
    with pytest.raises(ValidationError):
        StringTypesModel(
            topic="prod.orders.created",
            change="chg_001",
            team="Team-Commerce",
            doc="https://wiki",
            sla="x",
            tag="ok",
            status="pending",
        )


def test_document_url_and_sla_constraints():
    # invalid url scheme
    with pytest.raises(ValidationError):
        StringTypesModel(
            topic="prod.orders.created",
            change="chg_001",
            team="team-commerce",
            doc="ftp://wiki.company.com/streams/orders",
            sla="P99<200ms",
            tag="ok",
            status="pending",
        )

    # sla cannot be blank after strip
    with pytest.raises(ValidationError):
        StringTypesModel(
            topic="prod.orders.created",
            change="chg_001",
            team="team-commerce",
            doc="https://wiki",
            sla="   ",
            tag="ok",
            status="pending",
        )


def test_tag_and_status_patterns():
    # tag with space invalid
    with pytest.raises(ValidationError):
        StringTypesModel(
            topic="prod.orders.created",
            change="chg_001",
            team="team-commerce",
            doc="https://wiki",
            sla="ok",
            tag="pi i",
            status="pending",
        )

    # status must be one of pending|applied|failed
    with pytest.raises(ValidationError):
        StringTypesModel(
            topic="prod.orders.created",
            change="chg_001",
            team="team-commerce",
            doc="https://wiki",
            sla="ok",
            tag="ok",
            status="done",
        )


def test_partition_count_and_replication_factor_ranges():
    # valid
    m = IntTypesModel(
        partitions=12,
        replication_factor=3,
        retention_ms=604_800_000,
        min_insync_replicas=2,
        segment_ms=10_000,
        max_message_bytes=1_048_576,
    )
    assert m.partitions == 12 and m.replication_factor == 3

    # partitions above max
    with pytest.raises(ValidationError):
        IntTypesModel(
            partitions=2000,
            replication_factor=3,
            retention_ms=604_800_000,
            min_insync_replicas=2,
            segment_ms=10_000,
            max_message_bytes=1_048_576,
        )

    # replication_factor below min
    with pytest.raises(ValidationError):
        IntTypesModel(
            partitions=12,
            replication_factor=0,
            retention_ms=604_800_000,
            min_insync_replicas=2,
            segment_ms=10_000,
            max_message_bytes=1_048_576,
        )


def test_strict_int_and_other_ranges():
    # partitions as string should fail due to strict int
    with pytest.raises(ValidationError):
        IntTypesModel(
            partitions="12",  # type: ignore[arg-type]
            replication_factor=3,
            retention_ms=604_800_000,
            min_insync_replicas=2,
            segment_ms=10_000,
            max_message_bytes=1_048_576,
        )

    # retention below min
    with pytest.raises(ValidationError):
        IntTypesModel(
            partitions=12,
            replication_factor=3,
            retention_ms=999,
            min_insync_replicas=2,
            segment_ms=10_000,
            max_message_bytes=1_048_576,
        )

    # min_insync_replicas above max
    with pytest.raises(ValidationError):
        IntTypesModel(
            partitions=12,
            replication_factor=3,
            retention_ms=604_800_000,
            min_insync_replicas=11,
            segment_ms=10_000,
            max_message_bytes=1_048_576,
        )

    # segment_ms below min
    with pytest.raises(ValidationError):
        IntTypesModel(
            partitions=12,
            replication_factor=3,
            retention_ms=604_800_000,
            min_insync_replicas=2,
            segment_ms=999,
            max_message_bytes=1_048_576,
        )

    # max_message_bytes above max
    with pytest.raises(ValidationError):
        IntTypesModel(
            partitions=12,
            replication_factor=3,
            retention_ms=604_800_000,
            min_insync_replicas=2,
            segment_ms=10_000,
            max_message_bytes=100_000_001,
        )
