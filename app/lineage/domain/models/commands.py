"""데이터 리니지 Command — 도메인 의도를 표현하는 불변 스키마"""

from __future__ import annotations

from dataclasses import dataclass

from app.lineage.types import EdgeType, LinkConfidence, NodeId, NodeType
from app.shared.types import ProductId


@dataclass(frozen=True, slots=True)
class RegisterNodeCommand:
    """리니지 노드 등록 요청"""

    node_type: NodeType
    name: str
    product_id: ProductId | None = None
    metadata: dict[str, str] | None = None


@dataclass(frozen=True, slots=True)
class AddEdgeCommand:
    """리니지 엣지 추가 요청"""

    source_id: NodeId
    target_id: NodeId
    edge_type: EdgeType
    confidence: LinkConfidence = LinkConfidence.MANUAL
    description: str | None = None
    registered_by: str | None = None
