"""Schema Domain Models

이 모듈은 기능별로 분리된 도메인 모델들을 export합니다.
기존 코드와의 호환성을 위해 모든 모델을 여기서 import할 수 있습니다.
"""

# Enums and Types
# Internal Models (for infrastructure)
from .internal import (
    Reference,
    SchemaVersionInfo,
)

# Plan and Result Models
from .plan_result import (
    DomainSchemaApplyResult,
    DomainSchemaArtifact,
    DomainSchemaDiff,
    DomainSchemaPlan,
    DomainSchemaPlanItem,
    DomainSchemaUploadResult,
)

# Policy Models
from .policy import (
    DomainPolicyViolation,
    DomainSchemaCompatibilityIssue,
    DomainSchemaCompatibilityReport,
    DomainSchemaDeleteImpact,
    DomainSchemaImpactRecord,
)

# Specs and Batch
from .spec_batch import (
    DomainSchemaBatch,
    DomainSchemaSpec,
)
from .types_enum import (
    Actor,
    ChangeId,
    DomainCompatibilityMode,
    DomainEnvironment,
    DomainPlanAction,
    DomainSchemaSourceType,
    DomainSchemaType,
    DomainSubjectStrategy,
    FileReference,
    ReasonText,
    SchemaDefinition,
    SchemaHash,
    SchemaYamlText,
    SubjectName,
)

# Utilities
from .utils import (
    CompatibilityResult,
    DescribeResult,
    ensure_unique_subjects,
)

# Value Objects
from .value_objects import (
    DomainSchemaMetadata,
    DomainSchemaReference,
    DomainSchemaSource,
)

__all__ = [
    # Type Aliases
    "Actor",
    "ChangeId",
    # Utilities
    "CompatibilityResult",
    "DescribeResult",
    # Enums
    "DomainCompatibilityMode",
    "DomainEnvironment",
    "DomainPlanAction",
    # Policy Models
    "DomainPolicyViolation",
    # Result Models
    "DomainSchemaApplyResult",
    "DomainSchemaArtifact",
    "DomainSchemaBatch",
    "DomainSchemaCompatibilityIssue",
    "DomainSchemaCompatibilityReport",
    "DomainSchemaDeleteImpact",
    # Plan Models
    "DomainSchemaDiff",
    "DomainSchemaImpactRecord",
    # Value Objects
    "DomainSchemaMetadata",
    "DomainSchemaPlan",
    "DomainSchemaPlanItem",
    "DomainSchemaReference",
    "DomainSchemaSource",
    "DomainSchemaSourceType",
    # Specs and Batch
    "DomainSchemaSpec",
    "DomainSchemaType",
    "DomainSchemaUploadResult",
    "DomainSubjectStrategy",
    "FileReference",
    "ReasonText",
    # Internal Models
    "Reference",
    "SchemaDefinition",
    "SchemaHash",
    "SchemaVersionInfo",
    "SchemaYamlText",
    "SubjectName",
    "ensure_unique_subjects",
]
