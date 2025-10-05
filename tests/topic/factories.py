"""Topic 도메인 객체 팩토리"""

from __future__ import annotations

from app.topic.domain.models import (
    DomainCleanupPolicy,
    DomainEnvironment,
    DomainPlanAction,
    DomainTopicAction,
    DomainTopicBatch,
    DomainTopicConfig,
    DomainTopicMetadata,
    DomainTopicPlan,
    DomainTopicPlanItem,
    DomainTopicSpec,
)


def create_topic_metadata(
    owner: str = "team-test",
    doc: str | None = None,
    tags: tuple[str, ...] = (),
) -> DomainTopicMetadata:
    """토픽 메타데이터 생성"""
    return DomainTopicMetadata(
        owner=owner,
        doc=doc,
        tags=tags,
    )


def create_topic_config(
    partitions: int = 3,
    replication_factor: int = 2,
    cleanup_policy: DomainCleanupPolicy = DomainCleanupPolicy.DELETE,
    retention_ms: int | None = None,
    min_insync_replicas: int | None = None,
    max_message_bytes: int | None = None,
    segment_ms: int | None = None,
) -> DomainTopicConfig:
    """토픽 설정 생성"""
    return DomainTopicConfig(
        partitions=partitions,
        replication_factor=replication_factor,
        cleanup_policy=cleanup_policy,
        retention_ms=retention_ms,
        min_insync_replicas=min_insync_replicas,
        max_message_bytes=max_message_bytes,
        segment_ms=segment_ms,
    )


def create_topic_spec(
    name: str = "dev.test.topic",
    action: DomainTopicAction = DomainTopicAction.CREATE,
    config: DomainTopicConfig | None = None,
    metadata: DomainTopicMetadata | None = None,
) -> DomainTopicSpec:
    """토픽 명세 생성"""
    if action != DomainTopicAction.DELETE and config is None:
        config = create_topic_config()
    if action != DomainTopicAction.DELETE and metadata is None:
        metadata = create_topic_metadata()

    return DomainTopicSpec(
        name=name,
        action=action,
        config=config,
        metadata=metadata,
    )


def create_topic_batch(
    change_id: str = "test-change-001",
    env: DomainEnvironment = DomainEnvironment.DEV,
    specs: tuple[DomainTopicSpec, ...] | None = None,
) -> DomainTopicBatch:
    """토픽 배치 생성"""
    if specs is None:
        # 환경에 맞는 기본 스펙 생성
        specs = (create_topic_spec(name=f"{env.value}.test.topic"),)

    return DomainTopicBatch(
        change_id=change_id,
        env=env,
        specs=specs,
    )


def create_plan_item(
    name: str = "dev.test.topic",
    action: DomainPlanAction = DomainPlanAction.CREATE,
    diff: dict[str, str] | None = None,
    current_config: dict[str, str] | None = None,
    target_config: dict[str, str] | None = None,
) -> DomainTopicPlanItem:
    """계획 아이템 생성"""
    if diff is None:
        diff = {"status": "new→created"}

    return DomainTopicPlanItem(
        name=name,
        action=action,
        diff=diff,
        current_config=current_config,
        target_config=target_config,
    )


def create_topic_plan(
    change_id: str = "test-change-001",
    env: DomainEnvironment = DomainEnvironment.DEV,
    items: tuple[DomainTopicPlanItem, ...] | None = None,
    violations: tuple = (),
) -> DomainTopicPlan:
    """토픽 계획 생성"""
    if items is None:
        items = (create_plan_item(),)

    return DomainTopicPlan(
        change_id=change_id,
        env=env,
        items=items,
        violations=violations,
    )
