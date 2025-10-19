"""Topic Domain Policies

Policy validation framework for topic governance.

Structure:
- management/ - Policy storage, retrieval, versioning (CRUD)
- validation/ - Policy resolution and validation orchestration
- guardrail/ - Guardrail policy definitions
- naming/ - Naming policy definitions

Supports 3 policy types:
1. No policy - Skip validation (default)
2. Preset - Built-in presets (dev/stg/prod)
3. Custom - User-defined policies (UI + DB + versioning)
"""

# Management (policy CRUD)
from .management import IPolicyRepository, PolicyReference, PolicyStatus, PolicyType, StoredPolicy

# Validation (orchestration)
from .validation import (
    PolicyResolver,
    TopicPolicyValidator,
    create_full_validator,
    create_guardrail_only_validator,
    create_naming_only_validator,
)

__all__ = [
    # Management
    "IPolicyRepository",
    "PolicyReference",
    # Validation
    "PolicyResolver",
    "PolicyStatus",
    "PolicyType",
    "StoredPolicy",
    "TopicPolicyValidator",
    "create_full_validator",
    "create_guardrail_only_validator",
    "create_naming_only_validator",
]
