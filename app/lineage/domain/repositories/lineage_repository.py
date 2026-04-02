"""데이터 리니지 리포지토리 포트 — 도메인이 인프라에 요구하는 인터페이스"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.lineage.domain.models.lineage import LineageEdge, LineageGraph, LineageNode
from app.lineage.types import EdgeId, NodeId
from app.shared.types import ProductId


class ILineageRepository(ABC):
    """리니지 그래프 영속성 포트"""

    @abstractmethod
    async def save_node(self, node: LineageNode) -> None:
        """노드를 저장한다."""

    @abstractmethod
    async def save_edge(self, edge: LineageEdge) -> None:
        """엣지를 저장한다."""

    @abstractmethod
    async def find_node(self, node_id: NodeId) -> LineageNode | None:
        """ID로 노드를 조회한다."""

    @abstractmethod
    async def find_edges_from(self, source_id: NodeId) -> list[LineageEdge]:
        """특정 노드에서 나가는 엣지를 조회한다."""

    @abstractmethod
    async def find_edges_to(self, target_id: NodeId) -> list[LineageEdge]:
        """특정 노드로 들어오는 엣지를 조회한다."""

    @abstractmethod
    async def load_subgraph(
        self,
        root_id: NodeId,
        *,
        max_depth: int = 5,
    ) -> LineageGraph:
        """root 노드 기준으로 지정 깊이까지의 서브그래프를 로드한다."""

    @abstractmethod
    async def load_product_graph(self, product_id: ProductId) -> LineageGraph:
        """특정 Data Product를 중심으로 리니지 그래프를 로드한다."""

    @abstractmethod
    async def delete_node(self, node_id: NodeId) -> None:
        """노드와 연결된 엣지를 삭제한다."""

    @abstractmethod
    async def delete_edge(self, edge_id: EdgeId) -> None:
        """엣지를 삭제한다."""
