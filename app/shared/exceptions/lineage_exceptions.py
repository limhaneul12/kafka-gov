"""데이터 리니지 도메인 예외"""

from __future__ import annotations

from app.shared.exceptions.base_exceptions import DomainError, NotFoundError


class LineageError(DomainError):
    """리니지 도메인 예외 베이스"""


class CycleDetectedError(LineageError):
    """DAG에 순환이 감지됨"""

    def __init__(self, source_id: str, target_id: str) -> None:
        super().__init__(f"adding edge {source_id} → {target_id} would create a cycle")
        self.source_id = source_id
        self.target_id = target_id


class LineageNodeNotFoundError(NotFoundError):
    """리니지 노드를 찾을 수 없음"""

    def __init__(self, node_id: str) -> None:
        super().__init__("LineageNode", node_id)
        self.node_id = node_id


class LineageEdgeNotFoundError(NotFoundError):
    """리니지 엣지를 찾을 수 없음"""

    def __init__(self, edge_id: str) -> None:
        super().__init__("LineageEdge", edge_id)
        self.edge_id = edge_id


class DuplicateNodeError(LineageError):
    """중복 노드 추가 시도"""

    def __init__(self, node_id: str) -> None:
        super().__init__(f"node already exists: {node_id}")
        self.node_id = node_id


class SelfReferenceError(LineageError):
    """자기 참조 엣지 시도"""

    def __init__(self, node_id: str) -> None:
        super().__init__(f"self-referencing edge is not allowed: {node_id}")
        self.node_id = node_id
