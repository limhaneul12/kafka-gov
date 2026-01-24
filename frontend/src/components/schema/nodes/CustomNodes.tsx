import { Database, FileText, Server } from 'lucide-react';
import { NodeShell } from './NodeShell';

export const SchemaNode = ({ data }: { data: { label: string } }) => (
    <NodeShell icon={FileText} label={data.label} color="border-indigo-500" typeStr="Schema" />
);

export const TopicNode = ({ data }: { data: { label: string } }) => (
    <NodeShell icon={Database} label={data.label} color="border-amber-500" typeStr="Topic" />
);

export const ConsumerNode = ({ data }: { data: { label: string } }) => (
    <NodeShell icon={Server} label={data.label} color="border-emerald-500" typeStr="Consumer" />
);
