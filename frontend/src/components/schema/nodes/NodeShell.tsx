import React from 'react';
import { Handle, Position } from 'reactflow';

interface NodeShellProps {
    icon: React.ElementType;
    label: string;
    color: string;
    typeStr: string;
}

export const NodeShell: React.FC<NodeShellProps> = ({
    icon: Icon,
    label,
    color,
    typeStr,
}) => (
    <div
        className={`px-4 py-3 rounded-xl border-2 shadow-sm bg-white min-w-[150px] text-center ${color}`}
    >
        <Handle type="target" position={Position.Left} className="w-3 h-3 !bg-slate-400" />
        <div className="flex flex-col items-center gap-2">
            <div className={`p-2 rounded-full ${color.replace('border-', 'bg-').replace('-500', '-100')}`}>
                <Icon className={`w-5 h-5 ${color.replace('border-', 'text-')}`} />
            </div>
            <div>
                <p className="font-bold text-slate-700 text-sm">{label}</p>
                <p className="text-[10px] uppercase font-semibold text-slate-400 mt-1">{typeStr}</p>
            </div>
        </div>
        <Handle type="source" position={Position.Right} className="w-3 h-3 !bg-slate-400" />
    </div>
);
