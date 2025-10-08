"""Schema Interface - Request Schemas"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Annotated

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StrictStr,
    field_validator,
    model_validator,
)

from ..types.enums import (
    CompatibilityMode,
    Environment,
    SchemaSourceType,
    SchemaType,
    SubjectStrategy,
)
from ..types.type_hints import (
    ChangeId,
    ReasonText,
    SchemaDefinition,
    SchemaHash,
    SubjectName,
)
from .common import SchemaMetadata, SchemaReference, SchemaSource


class SchemaBatchItem(BaseModel):
    """스키마 배치 단일 항목"""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        str_min_length=1,
        str_strip_whitespace=True,
        json_schema_extra={
            "example": {
                "subject": "prod.orders.created-value",
                "type": "AVRO",
                "compatibility": "FULL",
                "schema": '{"type":"record","name":"Order","fields":[{"name":"id","type":"string"}]}',
                "references": [
                    {
                        "name": "common.Address",
                        "subject": "prod.common.address-value",
                        "version": 5,
                    }
                ],
                "metadata": {
                    "owner": "team-data-platform",
                    "doc": "https://wiki.company.com/schemas/order",
                },
            }
        },
    )

    subject: SubjectName
    type: SchemaType = Field(
        validation_alias=AliasChoices("schema_type", "type"),
        serialization_alias="type",
    )
    compatibility: CompatibilityMode | None = None
    schema_text: SchemaDefinition | None = Field(
        default=None,
        description="스키마 정의 텍스트",
        validation_alias=AliasChoices("schema", "schema_text"),
        serialization_alias="schema",
    )
    source: SchemaSource | None = None
    schema_hash: SchemaHash | None = Field(
        default=None,
        description="스키마 내용의 사전 계산된 해시",
    )
    references: list[SchemaReference] = Field(default_factory=list, max_length=16)
    metadata: SchemaMetadata | None = None
    reason: ReasonText | None = None
    dry_run_only: StrictBool = Field(
        default=False, description="true이면 dry-run에서만 검증하고 apply 시 제외"
    )

    @model_validator(mode="after")
    def validate_payload(self) -> SchemaBatchItem:
        """스키마 내용/소스 검증"""
        if not self.schema_text and not self.source:
            raise ValueError("schema or source must be provided")
        if self.schema_text and self.source and self.source.type is not SchemaSourceType.INLINE:
            raise ValueError("schema literal is only allowed with inline source or without source")
        return self

    @field_validator("references")
    @classmethod
    def validate_unique_reference_names(
        cls, value: Iterable[SchemaReference]
    ) -> list[SchemaReference]:
        """참조 이름 중복 검증"""
        references = list(value)
        names = [ref.name for ref in references]
        duplicates = {name for name in names if names.count(name) > 1}
        if duplicates:
            raise ValueError(f"duplicate reference name(s): {sorted(duplicates)}")
        return references


class SchemaBatchRequest(BaseModel):
    """스키마 배치 요청"""

    model_config = ConfigDict(
        extra="forbid",
        str_min_length=1,
        str_strip_whitespace=True,
        json_schema_extra={
            "example": {
                "kind": "SchemaBatch",
                "env": "prod",
                "change_id": "2025-09-25_001",
                "subjectStrategy": "TopicNameStrategy",
                "items": [
                    {
                        "subject": "prod.orders.created-value",
                        "type": "AVRO",
                        "compatibility": "FULL",
                        "schema": "{...}",
                        "metadata": {
                            "owner": "team-data-platform",
                            "doc": "https://wiki.company.com/schemas/order",
                        },
                    }
                ],
            }
        },
    )

    kind: StrictStr = Field(default="SchemaBatch", description="요청 종류")
    env: Environment
    change_id: ChangeId
    subject_strategy: SubjectStrategy = Field(
        default=SubjectStrategy.TOPIC_NAME,
        validation_alias=AliasChoices("subjectStrategy", "subject_strategy"),
        serialization_alias="subjectStrategy",
    )
    items: Annotated[
        list[SchemaBatchItem],
        Field(
            min_length=1,
            max_length=200,
            description="스키마 배치 항목",
            validation_alias=AliasChoices("items", "specs"),
            serialization_alias="items",
        ),
    ]

    @field_validator("kind")
    @classmethod
    def validate_kind(cls, value: StrictStr) -> StrictStr:
        """kind 필드 검증"""
        if value != "SchemaBatch":
            raise ValueError("kind must be 'SchemaBatch'")
        return value

    @field_validator("items")
    @classmethod
    def validate_unique_subjects(cls, items: list[SchemaBatchItem]) -> list[SchemaBatchItem]:
        """subject 중복 검증"""
        subjects = [item.subject for item in items]
        duplicates = {subject for subject in subjects if subjects.count(subject) > 1}
        if duplicates:
            raise ValueError(f"duplicate subjects detected: {sorted(duplicates)}")
        return items

    @model_validator(mode="after")
    def validate_env_consistency(self) -> SchemaBatchRequest:
        """환경 접두사 및 호환성 기본값 적용"""
        prefix = self.env.value
        adjusted_items: list[SchemaBatchItem] = []

        for item in self.items:
            subject_env = item.subject.split(".")[0]
            if subject_env != prefix:
                raise ValueError(
                    f"subject '{item.subject}' environment ({subject_env}) "
                    f"does not match batch environment ({prefix})"
                )

            if item.compatibility is None:
                default_mode = (
                    CompatibilityMode.FULL
                    if self.env is Environment.PROD
                    else CompatibilityMode.BACKWARD
                )
                adjusted_items.append(item.model_copy(update={"compatibility": default_mode}))
            else:
                adjusted_items.append(item)

        return self.model_copy(update={"items": adjusted_items})
