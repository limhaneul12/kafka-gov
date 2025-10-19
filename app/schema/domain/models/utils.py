"""Schema Models Utilities"""

from __future__ import annotations

from collections.abc import Iterable

from .internal import SchemaVersionInfo
from .policy import DomainSchemaCompatibilityReport
from .types_enum import SubjectName


def ensure_unique_subjects(subjects: Iterable[SubjectName]) -> None:
    """subject 중복 검증"""
    subject_list = list(subjects)
    duplicates = {subject for subject in subject_list if subject_list.count(subject) > 1}
    if duplicates:
        raise ValueError(f"duplicate subjects detected: {sorted(duplicates)}")


# Type Aliases for backward compatibility
CompatibilityResult = dict[SubjectName, DomainSchemaCompatibilityReport]
DescribeResult = dict[SubjectName, SchemaVersionInfo]
