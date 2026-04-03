"""데이터 리니지 도메인 모델 — End-to-End 데이터 흐름 추적

리니지는 데이터가 조직 안에서 어디서 발생하고, 어디로 흘러가는지를 추적한다.
Data Product 간의 의존 관계를 DAG(방향 비순환 그래프)로 표현한다.

기존 schema→topic→consumer 단방향 영향도 그래프를 대체하는 개념이다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from app.lineage.types import EdgeId, EdgeType, LinkConfidence, NodeId, NodeType
from app.shared.domain.value_objects import ProductId
from app.shared.exceptions.lineage_exceptions import (
    CycleDetectedError,
    DuplicateNodeError,
    LineageEdgeNotFoundError,
    LineageNodeNotFoundError,
    SelfReferenceError,
)


@dataclass(frozen=True, slots=True)
class LineageNode:
    """리니지 그래프의 노드 — 데이터 흐름의 참여자"""

    node_id: NodeId
    node_type: NodeType
    name: str
    product_id: ProductId | None = None
    metadata: dict[str, str] | None = None

    @property
    def is_data_product(self) -> bool:
        return self.node_type is NodeType.DATA_PRODUCT


@dataclass(frozen=True, slots=True)
class LineageEdge:
    """리니지 그래프의 엣지 — 데이터 흐름 방향"""

    edge_id: EdgeId
    source_id: NodeId
    target_id: NodeId
    edge_type: EdgeType
    confidence: LinkConfidence = LinkConfidence.MANUAL
    description: str | None = None
    registered_at: datetime | None = None
    registered_by: str | None = None

    def __post_init__(self) -> None:
        if self.source_id == self.target_id:
            raise SelfReferenceError(self.source_id)


@dataclass(slots=True)
class LineageGraph:
    """리니지 DAG — Data Product 간 데이터 흐름 그래프

    노드는 Data Product, Service, Database 등이고,
    엣지는 produces/consumes/derives_from 등의 관계를 나타낸다.

    이 그래프를 통해:
    - "이 스키마 필드를 바꾸면 어떤 서비스가 영향받는가" (impact analysis)
    - "이 데이터의 원천은 어디인가" (root cause tracking)
    - "이 서비스가 의존하는 모든 데이터는 무엇인가" (dependency map)
    을 답할 수 있다.
    """

    nodes: dict[NodeId, LineageNode] = field(default_factory=dict)
    edges: list[LineageEdge] = field(default_factory=list)

    # ------------------------------------------------------------------ #
    # 노드 관리
    # ------------------------------------------------------------------ #

    def add_node(self, node: LineageNode) -> None:
        if node.node_id in self.nodes:
            raise DuplicateNodeError(node.node_id)
        self.nodes[node.node_id] = node

    def remove_node(self, node_id: NodeId) -> None:
        if node_id not in self.nodes:
            raise LineageNodeNotFoundError(node_id)
        # 연결된 엣지도 함께 제거
        self.edges = [e for e in self.edges if e.source_id != node_id and e.target_id != node_id]
        del self.nodes[node_id]

    # ------------------------------------------------------------------ #
    # 엣지 관리
    # ------------------------------------------------------------------ #

    def add_edge(self, edge: LineageEdge) -> None:
        if edge.source_id not in self.nodes:
            raise LineageNodeNotFoundError(edge.source_id)
        if edge.target_id not in self.nodes:
            raise LineageNodeNotFoundError(edge.target_id)

        # 순환 검사
        if self._would_create_cycle(edge.source_id, edge.target_id):
            raise CycleDetectedError(edge.source_id, edge.target_id)

        self.edges.append(edge)

    def remove_edge(self, edge_id: EdgeId) -> None:
        original_len = len(self.edges)
        self.edges = [e for e in self.edges if e.edge_id != edge_id]
        if len(self.edges) == original_len:
            raise LineageEdgeNotFoundError(edge_id)

    # ------------------------------------------------------------------ #
    # 탐색 (Impact Analysis)
    # ------------------------------------------------------------------ #

    def upstream(self, node_id: NodeId, max_depth: int = 10) -> list[LineageNode]:
        """주어진 노드의 상류(데이터 원천 방향) 노드들을 반환한다."""
        return self._traverse(node_id, direction="upstream", max_depth=max_depth)

    def downstream(self, node_id: NodeId, max_depth: int = 10) -> list[LineageNode]:
        """주어진 노드의 하류(데이터 소비 방향) 노드들을 반환한다."""
        return self._traverse(node_id, direction="downstream", max_depth=max_depth)

    def impact_of(self, node_id: NodeId) -> ImpactReport:
        """특정 노드 변경 시 영향 받는 모든 하류 노드를 분석한다."""
        affected = self.downstream(node_id)
        data_products = [n for n in affected if n.is_data_product]
        services = [n for n in affected if n.node_type is NodeType.SERVICE]

        return ImpactReport(
            source_node_id=node_id,
            affected_products=data_products,
            affected_services=services,
            total_affected=len(affected),
        )

    # ------------------------------------------------------------------ #
    # 내부 헬퍼
    # ------------------------------------------------------------------ #

    def _traverse(self, start_id: NodeId, *, direction: str, max_depth: int) -> list[LineageNode]:
        visited: set[NodeId] = set()
        result: list[LineageNode] = []
        queue: list[tuple[NodeId, int]] = [(start_id, 0)]

        while queue:
            current_id, depth = queue.pop(0)
            if current_id in visited or depth > max_depth:
                continue
            visited.add(current_id)

            if current_id != start_id and current_id in self.nodes:
                result.append(self.nodes[current_id])

            queue.extend(
                (neighbor_id, depth + 1)
                for neighbor_id in self._neighbors(current_id, direction)
                if neighbor_id not in visited
            )

        return result

    def _neighbors(self, node_id: NodeId, direction: str) -> list[NodeId]:
        if direction == "upstream":
            return [e.source_id for e in self.edges if e.target_id == node_id]
        return [e.target_id for e in self.edges if e.source_id == node_id]

    def _would_create_cycle(self, source_id: NodeId, target_id: NodeId) -> bool:
        """target → source 경로가 존재하면 순환이 생긴다."""
        visited: set[NodeId] = set()
        queue: list[NodeId] = [target_id]

        while queue:
            current = queue.pop(0)
            if current == source_id:
                return True
            if current in visited:
                continue
            visited.add(current)
            queue.extend(e.target_id for e in self.edges if e.source_id == current)

        return False


# ============================================================================
# 분석 결과 모델
# ============================================================================


@dataclass(frozen=True, slots=True)
class ImpactReport:
    """변경 영향도 분석 결과"""

    source_node_id: NodeId
    affected_products: list[LineageNode]
    affected_services: list[LineageNode]
    total_affected: int

    @property
    def has_impact(self) -> bool:
        return self.total_affected > 0

    @property
    def is_high_impact(self) -> bool:
        return self.total_affected >= 5 or len(self.affected_products) >= 3
