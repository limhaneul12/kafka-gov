"""Schema Value Objects"""

from __future__ import annotations

from dataclasses import dataclass

from .types_enum import (
    DomainSchemaSourceType,
    FileReference,
    SchemaDefinition,
    SchemaYamlText,
    SubjectName,
)


@dataclass(frozen=True, slots=True)
class DomainSchemaMetadata:
    """스키마 메타데이터 - Value Object"""

    owner: str
    doc: str | None = None
    tags: tuple[str, ...] = ()
    description: str | None = None

    def __post_init__(self) -> None:
        if not self.owner:
            raise ValueError("owner is required")


@dataclass(frozen=True, slots=True)
class DomainSchemaReference:
    """스키마 참조 정보 - Value Object"""

    name: str
    subject: SubjectName
    version: int

    def __post_init__(self) -> None:
        if self.version < 1:
            raise ValueError("reference version must be >= 1")
        if not self.name:
            raise ValueError("reference name is required")
        if not self.subject:
            raise ValueError("reference subject is required")


@dataclass(frozen=True, slots=True)
class DomainSchemaSource:
    """스키마 소스 정의 - Value Object"""

    type: DomainSchemaSourceType
    inline: SchemaDefinition | None = None
    file: FileReference | None = None
    yaml: SchemaYamlText | None = None

    def __post_init__(self) -> None:
        if self.type is DomainSchemaSourceType.INLINE:
            if not self.inline:
                raise ValueError("inline source requires inline content")
            if self.file or self.yaml:
                raise ValueError("inline source cannot include file or yaml data")
        elif self.type is DomainSchemaSourceType.FILE:
            if not self.file:
                raise ValueError("file source requires file reference")
            if self.inline or self.yaml:
                raise ValueError("file source cannot include inline or yaml data")
        elif self.type is DomainSchemaSourceType.YAML:
            if not self.yaml:
                raise ValueError("yaml source requires yaml content")
            if self.inline or self.file:
                raise ValueError("yaml source cannot include inline or file data")
