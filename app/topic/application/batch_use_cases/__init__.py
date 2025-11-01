"""배치 작업 use cases"""

# 기존 이름도 export (하위 호환성)
from .batch_apply import TopicBatchApplyUseCase, TopicBatchApplyUseCase as BatchApplyUseCase
from .batch_apply_yaml import (
    TopicBatchApplyFromYAMLUseCase,
    TopicBatchApplyFromYAMLUseCase as BatchApplyYamlUseCase,
)
from .batch_dry_run import TopicBatchDryRunUseCase, TopicBatchDryRunUseCase as BatchDryRunUseCase
from .bulk_delete import TopicBulkDeleteUseCase, TopicBulkDeleteUseCase as BulkDeleteUseCase

__all__ = [
    # 새 이름
    "BatchApplyUseCase",
    "BatchApplyYamlUseCase",
    "BatchDryRunUseCase",
    "BulkDeleteUseCase",
    # 기존 이름 (하위 호환성)
    "TopicBatchApplyFromYAMLUseCase",
    "TopicBatchApplyUseCase",
    "TopicBatchDryRunUseCase",
    "TopicBulkDeleteUseCase",
]
