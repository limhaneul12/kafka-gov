"""Topic Domain Models

이 모듈은 기능별로 분리된 도메인 모델들을 export합니다.
기존 코드와의 호환성을 위해 모든 모델을 여기서 import할 수 있습니다.
"""

# Enums and Types
# Config and Metadata
from .config import (
    DomainTopicConfig,
    DomainTopicMetadata,
)

# Metrics
from .metrics import (
    ClusterMetrics,
    PartitionDetails,
    TopicMeta,
    TopicMetrics,
)

# Plan and Result
from .plan import (
    DomainTopicApplyResult,
    DomainTopicPlan,
    DomainTopicPlanItem,
)

# Report
from .report import (
    DryRunItemReport,
    DryRunReport,
    DryRunSummary,
    ViolationDetail,
)

# Spec and Batch
from .spec_batch import (
    DomainTopicBatch,
    DomainTopicSpec,
)
from .types_enum import (
    ChangeId,
    DBMetadata,
    DocumentUrl,
    DomainCleanupPolicy,
    DomainEnvironment,
    DomainPlanAction,
    DomainTopicAction,
    KafkaMetadata,
    TeamName,
    TopicName,
)

__all__ = [
    # Type Aliases
    "ChangeId",
    "DBMetadata",
    "DocumentUrl",
    # Enums
    "DomainCleanupPolicy",
    "DomainEnvironment",
    "DomainPlanAction",
    "DomainTopicAction",
    # Result
    "DomainTopicApplyResult",
    "DomainTopicBatch",
    # Config and Metadata
    "DomainTopicConfig",
    "DomainTopicMetadata",
    # Metrics
    "ClusterMetrics",
    "PartitionDetails",
    "TopicMeta",
    "TopicMetrics",
    # Plan
    "DomainTopicPlan",
    "DomainTopicPlanItem",
    # Spec and Batch
    "DomainTopicSpec",
    # Report
    "DryRunItemReport",
    "DryRunReport",
    "DryRunSummary",
    "KafkaMetadata",
    "TeamName",
    "TopicName",
    "ViolationDetail",
]
