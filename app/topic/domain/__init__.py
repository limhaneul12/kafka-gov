"""Topic Domain Layer

도메인 모델, 서비스, 정책, 리포지토리 인터페이스를 포함합니다.

Structure:
- models.py - Domain entities and value objects
- services.py - Domain services
- utils.py - Domain utility functions
- policies/ - Policy validation (naming, guardrail)
- repositories/ - Repository interfaces

"""

# Domain Models
from .models import (
    ChangeId,
    DomainCleanupPolicy,
    DomainEnvironment,
    DomainPlanAction,
    DomainTopicAction,
    DomainTopicApplyResult,
    DomainTopicBatch,
    DomainTopicConfig,
    DomainTopicPlan,
    DomainTopicPlanItem,
    DomainTopicSpec,
    TopicName,
)

# Repositories
from .repositories import (
    IAuditRepository,
    IPolicyRepository,
    ITopicMetadataRepository,
    ITopicRepository,
)

# Domain Services
from .services import TopicDiffService, TopicPlannerService

# Utilities
from .utils import (
    calculate_dict_diff,
    format_diff_string,
    merge_configs,
    validate_partition_change,
    validate_replication_factor_change,
)

__all__ = [
    # Models
    "ChangeId",
    "DomainCleanupPolicy",
    "DomainEnvironment",
    "DomainPlanAction",
    "DomainTopicAction",
    "DomainTopicApplyResult",
    "DomainTopicBatch",
    "DomainTopicConfig",
    "DomainTopicPlan",
    "DomainTopicPlanItem",
    "DomainTopicSpec",
    # Repositories
    "IAuditRepository",
    "IPolicyRepository",
    "ITopicMetadataRepository",
    "ITopicRepository",
    # Services
    "TopicDiffService",
    "TopicName",
    "TopicPlannerService",
    # Utilities
    "calculate_dict_diff",
    "format_diff_string",
    "merge_configs",
    "validate_partition_change",
    "validate_replication_factor_change",
]
