import { useMemo } from 'react';
import ReactFlow, {
    Background,
    Controls,
} from 'reactflow';
import 'reactflow/dist/style.css';
import type { GraphLink, GraphNode } from '../../types/schema';
import { SchemaNode, TopicNode, ConsumerNode } from './nodes/CustomNodes';
import { calculateGraphLayout } from '../../utils/graphLayout';

interface ImpactGraphProps {
    nodes: GraphNode[];
    links: GraphLink[];
}

export default function ImpactGraph({ nodes: rawNodes, links: rawLinks }: ImpactGraphProps) {
    const nodeTypes = useMemo(
        () => ({
            SCHEMA: SchemaNode,
            TOPIC: TopicNode,
            CONSUMER: ConsumerNode,
        }),
        []
    );

    // Simple Level-based Layout Calculation
    const { nodes, edges } = useMemo(
        () => calculateGraphLayout(rawNodes, rawLinks),
        [rawNodes, rawLinks]
    );

    return (
        <div className="w-full h-[600px] border border-slate-200 rounded-xl bg-slate-50 overflow-hidden shadow-inner">
            <ReactFlow
                nodes={nodes}
                edges={edges}
                nodeTypes={nodeTypes}
                fitView
                attributionPosition="bottom-right"
                edgesUpdatable={false}
                nodesConnectable={false}
                nodesDraggable={false}
            >
                <Background gap={16} size={1} color="#e2e8f0" />
                <Controls />
            </ReactFlow>
        </div>
    );
}
