"""리니지 영향도 분석 유스케이스"""

from __future__ import annotations

import logging

from app.lineage.domain.models.lineage import ImpactReport, LineageGraph, LineageNode
from app.lineage.domain.repositories.lineage_repository import ILineageRepository
from app.lineage.types import NodeId
from app.shared.exceptions.lineage_exceptions import LineageNodeNotFoundError
from app.shared.types import ProductId

logger = logging.getLogger(__name__)


class GetImpactUseCase:
    """특정 노드 변경 시 하류 영향도 분석

    "이 스키마 필드를 바꾸면 어떤 서비스가 영향받는가"에 대한 답.
    """

    def __init__(self, repository: ILineageRepository) -> None:
        self._repository = repository

    async def execute(self, node_id: NodeId, max_depth: int = 10) -> ImpactReport:
        node = await self._repository.find_node(node_id)
        if node is None:
            raise LineageNodeNotFoundError(node_id)

        graph = await self._repository.load_subgraph(node_id, max_depth=max_depth)
        report = graph.impact_of(node_id)

        logger.info(
            "impact_analysis_completed",
            extra={
                "source": node_id,
                "total_affected": report.total_affected,
                "is_high_impact": report.is_high_impact,
            },
        )
        return report


class GetUpstreamUseCase:
    """특정 노드의 상류(데이터 원천) 추적

    "이 데이터의 원천은 어디인가"에 대한 답.
    """

    def __init__(self, repository: ILineageRepository) -> None:
        self._repository = repository

    async def execute(self, node_id: NodeId, max_depth: int = 10) -> list[LineageNode]:
        node = await self._repository.find_node(node_id)
        if node is None:
            raise LineageNodeNotFoundError(node_id)

        graph = await self._repository.load_subgraph(node_id, max_depth=max_depth)
        return graph.upstream(node_id, max_depth=max_depth)


class GetProductLineageUseCase:
    """Data Product 중심 리니지 그래프 조회"""

    def __init__(self, repository: ILineageRepository) -> None:
        self._repository = repository

    async def execute(self, product_id: ProductId) -> LineageGraph:
        return await self._repository.load_product_graph(product_id)
