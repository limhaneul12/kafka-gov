"""리니지 그래프 관리 유스케이스 — 노드/엣지 등록·삭제"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime

from app.lineage.domain.models.commands import AddEdgeCommand, RegisterNodeCommand
from app.lineage.domain.models.lineage import LineageEdge, LineageNode
from app.lineage.domain.repositories.lineage_repository import ILineageRepository
from app.lineage.types import NodeId
from app.shared.exceptions.lineage_exceptions import LineageNodeNotFoundError

logger = logging.getLogger(__name__)


class RegisterNodeUseCase:
    """리니지 노드 등록"""

    def __init__(self, repository: ILineageRepository) -> None:
        self._repository = repository

    async def execute(self, command: RegisterNodeCommand) -> LineageNode:
        node = LineageNode(
            node_id=f"ln-{uuid.uuid4().hex[:12]}",
            node_type=command.node_type,
            name=command.name,
            product_id=command.product_id,
            metadata=command.metadata,
        )

        await self._repository.save_node(node)

        logger.info(
            "lineage_node_registered",
            extra={"node_id": node.node_id, "type": command.node_type},
        )
        return node


class AddEdgeUseCase:
    """리니지 엣지 추가

    비즈니스 규칙:
    - source/target 노드가 존재해야 한다
    - 순환(cycle)이 생기면 거부한다
    """

    def __init__(self, repository: ILineageRepository) -> None:
        self._repository = repository

    async def execute(self, command: AddEdgeCommand) -> LineageEdge:
        source = await self._repository.find_node(command.source_id)
        if source is None:
            raise LineageNodeNotFoundError(command.source_id)

        target = await self._repository.find_node(command.target_id)
        if target is None:
            raise LineageNodeNotFoundError(command.target_id)

        edge = LineageEdge(
            edge_id=f"le-{uuid.uuid4().hex[:12]}",
            source_id=command.source_id,
            target_id=command.target_id,
            edge_type=command.edge_type,
            confidence=command.confidence,
            description=command.description,
            registered_at=datetime.now(),
            registered_by=command.registered_by,
        )

        await self._repository.save_edge(edge)

        logger.info(
            "lineage_edge_added",
            extra={
                "edge_id": edge.edge_id,
                "source": command.source_id,
                "target": command.target_id,
                "type": command.edge_type,
            },
        )
        return edge


class RemoveNodeUseCase:
    """리니지 노드 삭제 (연결된 엣지도 함께 삭제)"""

    def __init__(self, repository: ILineageRepository) -> None:
        self._repository = repository

    async def execute(self, node_id: NodeId) -> None:
        node = await self._repository.find_node(node_id)
        if node is None:
            raise LineageNodeNotFoundError(node_id)

        await self._repository.delete_node(node_id)

        logger.info("lineage_node_removed", extra={"node_id": node_id})
