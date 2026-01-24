import type { Node, Edge } from 'reactflow';
import type { GraphLink, GraphNode } from '../types/schema';

interface GraphLayoutResult {
    nodes: Node[];
    edges: Edge[];
}

export const calculateGraphLayout = (rawNodes: GraphNode[], rawLinks: GraphLink[]): GraphLayoutResult => {
    // 1. Filter nodes by type
    const schemaNodes = rawNodes.filter((n) => n.type === 'SCHEMA');
    const topicNodes = rawNodes.filter((n) => n.type === 'TOPIC');
    const consumerNodes = rawNodes.filter((n) => n.type === 'CONSUMER');

    // 2. Layout constants
    const LAYOUT_X_GAP = 300;
    const LAYOUT_Y_GAP = 120;

    // 3. Position calculator
    const calcPos = (layerIndex: number, itemIndex: number, totalInLayer: number) => ({
        x: layerIndex * LAYOUT_X_GAP,
        y: (itemIndex - (totalInLayer - 1) / 2) * LAYOUT_Y_GAP,
    });

    // 4. Generate Flow Nodes
    const flowNodes: Node[] = [
        ...schemaNodes.map((n, i) => ({
            id: n.id,
            type: 'SCHEMA',
            position: calcPos(0, i, schemaNodes.length),
            data: { label: n.label },
        })),
        ...topicNodes.map((n, i) => ({
            id: n.id,
            type: 'TOPIC',
            position: calcPos(1, i, topicNodes.length),
            data: { label: n.label },
        })),
        ...consumerNodes.map((n, i) => ({
            id: n.id,
            type: 'CONSUMER',
            position: calcPos(2, i, consumerNodes.length),
            data: { label: n.label },
        })),
    ];

    // 5. Generate Flow Edges
    const flowEdges: Edge[] = rawLinks.map((l, i) => ({
        id: `e-${i}`,
        source: l.source,
        target: l.target,
        animated: true,
        style: { stroke: '#94a3b8', strokeWidth: 2 },
    }));

    return { nodes: flowNodes, edges: flowEdges };
};
