"""Schema 도메인 객체 팩토리"""

from __future__ import annotations

from app.schema.domain.models import (
    DomainCompatibilityMode,
    DomainEnvironment,
    DomainSchemaBatch,
    DomainSchemaMetadata,
    DomainSchemaReference,
    DomainSchemaSource,
    DomainSchemaSourceType,
    DomainSchemaSpec,
    DomainSchemaType,
    DomainSubjectStrategy,
)


def create_schema_metadata(
    owner: str = "team-test",
    doc: str | None = None,
    tags: tuple[str, ...] = (),
    description: str | None = None,
) -> DomainSchemaMetadata:
    """스키마 메타데이터 생성"""
    return DomainSchemaMetadata(
        owner=owner,
        doc=doc,
        tags=tags,
        description=description,
    )


def create_schema_reference(
    name: str = "TestRef",
    subject: str = "dev.test.reference",
    version: int = 1,
) -> DomainSchemaReference:
    """스키마 참조 생성"""
    return DomainSchemaReference(
        name=name,
        subject=subject,
        version=version,
    )


def create_schema_source(
    source_type: DomainSchemaSourceType = DomainSchemaSourceType.INLINE,
    inline: str | None = '{"type": "record", "name": "Test"}',
    file: str | None = None,
    yaml: str | None = None,
) -> DomainSchemaSource:
    """스키마 소스 생성"""
    return DomainSchemaSource(
        type=source_type,
        inline=inline,
        file=file,
        yaml=yaml,
    )


def create_schema_spec(
    subject: str = "dev.test-subject",
    schema_type: DomainSchemaType = DomainSchemaType.AVRO,
    compatibility: DomainCompatibilityMode = DomainCompatibilityMode.BACKWARD,
    schema: str | None = '{"type": "record", "name": "Test", "fields": []}',
    source: DomainSchemaSource | None = None,
    references: tuple[DomainSchemaReference, ...] = (),
    metadata: DomainSchemaMetadata | None = None,
    reason: str | None = None,
    dry_run_only: bool = False,
) -> DomainSchemaSpec:
    """스키마 명세 생성"""
    if metadata is None:
        metadata = create_schema_metadata()

    return DomainSchemaSpec(
        subject=subject,
        schema_type=schema_type,
        compatibility=compatibility,
        schema=schema,
        source=source,
        references=references,
        metadata=metadata,
        reason=reason,
        dry_run_only=dry_run_only,
    )


def create_schema_batch(
    change_id: str = "test-change-001",
    env: DomainEnvironment = DomainEnvironment.DEV,
    subject_strategy: DomainSubjectStrategy = DomainSubjectStrategy.TOPIC_NAME,
    specs: tuple[DomainSchemaSpec, ...] | None = None,
) -> DomainSchemaBatch:
    """스키마 배치 생성"""
    if specs is None:
        specs = (create_schema_spec(subject=f"{env.value}.test-subject"),)

    return DomainSchemaBatch(
        change_id=change_id,
        env=env,
        subject_strategy=subject_strategy,
        specs=specs,
    )
