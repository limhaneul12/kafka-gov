import Badge from "../../ui/Badge";
import Button from "../../ui/Button";
import { Eye, History, Play, Trash2 } from "lucide-react";
import type { SchemaPolicyRecord } from "../../../types/schemaPolicy";

interface SchemaPolicyListProps {
    policies: SchemaPolicyRecord[];
    loading: boolean;
    onViewDetail: (policy: SchemaPolicyRecord) => void;
    onViewHistory: (policy: SchemaPolicyRecord) => void;
    onActivate: (policy: SchemaPolicyRecord) => void;
    onDelete: (policy: SchemaPolicyRecord) => void;
}

export default function SchemaPolicyList({
    policies,
    loading,
    onViewDetail,
    onViewHistory,
    onActivate,
    onDelete,
}: SchemaPolicyListProps) {
    if (loading) {
        return <div className="py-12 text-center text-gray-500">Loading policies...</div>;
    }

    if (policies.length === 0) {
        return (
            <div className="py-12 text-center text-gray-500 border-2 border-dashed rounded-xl">
                No schema policies found.
            </div>
        );
    }

    return (
        <div className="overflow-x-auto">
            <table className="w-full text-left">
                <thead className="border-b bg-gray-50 text-xs font-semibold uppercase text-gray-600">
                    <tr>
                        <th className="px-6 py-3">Policy Name</th>
                        <th className="px-6 py-3">Type</th>
                        <th className="px-6 py-3">Environment</th>
                        <th className="px-6 py-3">Version</th>
                        <th className="px-6 py-3">Status</th>
                        <th className="px-6 py-3 text-right">Actions</th>
                    </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                    {policies.map((policy) => (
                        <tr key={`${policy.policy_id}-${policy.version}`} className="hover:bg-gray-50">
                            <td className="px-6 py-4">
                                <div className="font-medium text-gray-900">{policy.name}</div>
                            </td>
                            <td className="px-6 py-4 capitalize">
                                <Badge variant={policy.policy_type === "lint" ? "info" : "default"}>
                                    {policy.policy_type}
                                </Badge>
                            </td>
                            <td className="px-6 py-4 capitalize">
                                <Badge className="font-normal border-gray-200 text-gray-600 bg-gray-50 border">
                                    {policy.target_environment}
                                </Badge>
                            </td>
                            <td className="px-6 py-4">
                                <span className="text-sm font-mono text-gray-500">v{policy.version}</span>
                            </td>
                            <td className="px-6 py-4">
                                <Badge
                                    variant={
                                        policy.status === "active"
                                            ? "success"
                                            : policy.status === "draft"
                                                ? "info"
                                                : "default"
                                    }
                                >
                                    {policy.status}
                                </Badge>
                            </td>
                            <td className="px-6 py-4 text-right">
                                <div className="flex justify-end gap-1">
                                    <Button variant="ghost" size="sm" onClick={() => onViewDetail(policy)}>
                                        <Eye className="h-4 w-4" />
                                    </Button>
                                    <Button variant="ghost" size="sm" onClick={() => onViewHistory(policy)}>
                                        <History className="h-4 w-4" />
                                    </Button>
                                    {policy.status === "draft" && (
                                        <Button variant="ghost" size="sm" onClick={() => onActivate(policy)} className="text-green-600">
                                            <Play className="h-4 w-4" />
                                        </Button>
                                    )}
                                    <Button variant="ghost" size="sm" onClick={() => onDelete(policy)} className="text-gray-400 hover:text-red-600">
                                        <Trash2 className="h-4 w-4" />
                                    </Button>
                                </div>
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}
