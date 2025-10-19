"""Schema Spec and Batch Models"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from .types_enum import (
    ChangeId,
    DomainCompatibilityMode,
    DomainEnvironment,
    DomainSchemaSourceType,
    DomainSchemaType,
    DomainSubjectStrategy,
    ReasonText,
    SchemaDefinition,
    SchemaHash,
    SubjectName,
)
from .value_objects import (
    DomainSchemaMetadata,
    DomainSchemaReference,
    DomainSchemaSource,
)


@dataclass(frozen=True, slots=True)
class DomainSchemaSpec:
    """스키마 등록 명세 - Value Object"""

    subject: SubjectName
    schema_type: DomainSchemaType
    compatibility: DomainCompatibilityMode
    schema: SchemaDefinition | None = None
    source: DomainSchemaSource | None = None
    schema_hash: SchemaHash | None = None
    references: tuple[DomainSchemaReference, ...] = ()
    metadata: DomainSchemaMetadata | None = None
    reason: ReasonText | None = None
    dry_run_only: bool = False

    def __post_init__(self) -> None:
        if not self.subject:
            raise ValueError("subject is required")

        if not (self.schema or self.source):
            raise ValueError("schema spec must provide schema or source")

        if self.schema and self.source and self.source.type is not DomainSchemaSourceType.INLINE:
            raise ValueError("schema literal is only allowed when source is inline or omitted")

    @property
    def environment(self) -> DomainEnvironment:
        """subject 접두사로부터 환경을 추론"""
        env_prefix = self.subject.split(".")[0]
        return DomainEnvironment(env_prefix)

    def fingerprint(self) -> SchemaHash:
        """스키마 명세 지문 생성"""
        content = f"{self.subject}:{self.schema_type}:{self.compatibility}"
        if self.schema:
            content += f":{self.schema}"
        if self.source:
            content += f":source:{self.source.type}:{self.source.inline or self.source.file or self.source.yaml}"
        if self.references:
            ref_digest = ",".join(
                f"{ref.name}:{ref.subject}:{ref.version}"
                for ref in sorted(self.references, key=lambda r: r.name)
            )
            content += f":refs:{ref_digest}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]


@dataclass(frozen=True, slots=True)
class DomainSchemaBatch:
    """스키마 배치 - Aggregate Root"""

    change_id: ChangeId
    env: DomainEnvironment
    subject_strategy: DomainSubjectStrategy
    specs: tuple[DomainSchemaSpec, ...]

    def __post_init__(self) -> None:
        if not self.change_id:
            raise ValueError("change_id is required")
        if not self.specs:
            raise ValueError("specs cannot be empty")

        subjects = [spec.subject for spec in self.specs]
        duplicates = {subject for subject in subjects if subjects.count(subject) > 1}
        if duplicates:
            raise ValueError(f"duplicate subjects detected: {sorted(duplicates)}")

        for spec in self.specs:
            if spec.environment != self.env:
                raise ValueError(
                    f"spec environment {spec.environment.value} does not match batch environment {self.env.value}"
                )

    def fingerprint(self) -> SchemaHash:
        """배치 지문 생성"""
        spec_fingerprints = sorted(spec.fingerprint() for spec in self.specs)
        content = f"{self.change_id}:{self.env.value}:{self.subject_strategy.value}:{':'.join(spec_fingerprints)}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
