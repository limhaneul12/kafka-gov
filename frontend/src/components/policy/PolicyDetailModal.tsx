import { useState, useEffect } from "react";
import Button from "../ui/Button";
import Badge from "../ui/Badge";
import Loading from "../ui/Loading";
import { policiesAPI } from "../../services/api";
import {
  X,
  History,
  Play,
  Archive,
  RotateCcw,
  Trash2,
  Edit,
  CheckCircle,
} from "lucide-react";

interface PolicyVersion {
  policy_id: string;
  policy_type: string;
  version: number;
  status: "DRAFT" | "ACTIVE" | "ARCHIVED";
  name: string;
  description: string;
  content: Record<string, unknown>;
  created_by: string;
  created_at: string;
  updated_at: string | null;
}

interface PolicyDetailModalProps {
  isOpen: boolean;
  onClose: () => void;
  policyId: string;
  onEdit: (policy: PolicyVersion) => void;
  onRefresh: () => void;
  autoShowVersions?: boolean;
}

export default function PolicyDetailModal({
  isOpen,
  onClose,
  policyId,
  onEdit,
  onRefresh,
  autoShowVersions = false,
}: PolicyDetailModalProps) {
  const [policy, setPolicy] = useState<PolicyVersion | null>(null);
  const [versions, setVersions] = useState<PolicyVersion[]>([]);
  const [loading, setLoading] = useState(true);
  const [showVersions, setShowVersions] = useState(autoShowVersions);

  useEffect(() => {
    if (isOpen && policyId) {
      loadPolicy();
      loadVersions();
      setShowVersions(autoShowVersions);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen, policyId, autoShowVersions]);

  const loadPolicy = async () => {
    try {
      setLoading(true);
      const response = await policiesAPI.get(policyId);
      console.log("Policy loaded:", response.data);
      setPolicy(response.data.policy);
    } catch (error: any) {
      console.error("Failed to load policy:", error);
      alert(`Failed to load policy: ${error.response?.data?.detail || error.message}`);
      onClose();
    } finally {
      setLoading(false);
    }
  };

  const loadVersions = async () => {
    try {
      // Get version history
      const versionResponse = await fetch(`/api/v1/policies/${policyId}/versions`);
      if (versionResponse.ok) {
        const data = await versionResponse.json();
        setVersions(data.versions || []);
      }
    } catch (error) {
      console.error("Failed to load versions:", error);
    }
  };

  const handleActivate = async (version?: number) => {
    if (!confirm(`Activate policy ${version ? `version ${version}` : ""}?`)) return;

    try {
      await policiesAPI.activate(policyId, version);
      await loadPolicy();
      await loadVersions();
      onRefresh();
    } catch (error) {
      console.error("Failed to activate policy:", error);
      alert("Failed to activate policy");
    }
  };

  const handleArchive = async () => {
    if (!confirm("Archive this policy? It will no longer be active.")) return;

    try {
      await fetch(`/api/v1/policies/${policyId}/archive`, { method: "POST" });
      await loadPolicy();
      await loadVersions();
      onRefresh();
    } catch (error) {
      console.error("Failed to archive policy:", error);
      alert("Failed to archive policy");
    }
  };

  const handleDelete = async () => {
    if (!confirm("Delete this DRAFT policy? This action cannot be undone.")) return;

    try {
      await policiesAPI.delete(policyId);
      onRefresh();
      onClose();
    } catch (error) {
      console.error("Failed to delete policy:", error);
      alert("Failed to delete policy. Only DRAFT policies can be deleted.");
    }
  };

  const handleRollback = async (targetVersion: number) => {
    if (
      !confirm(
        `Rollback to version ${targetVersion}? This will create a new DRAFT version with that content.`
      )
    )
      return;

    try {
      await fetch(`/api/v1/policies/${policyId}/rollback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ target_version: targetVersion }),
      });
      await loadPolicy();
      await loadVersions();
      onRefresh();
    } catch (error) {
      console.error("Failed to rollback policy:", error);
      alert("Failed to rollback policy");
    }
  };

  const getStatusBadgeVariant = (status: string) => {
    switch (status) {
      case "ACTIVE":
        return "success";
      case "DRAFT":
        return "warning";
      case "ARCHIVED":
        return "default";
      default:
        return "default";
    }
  };

  if (!isOpen) return null;

  if (loading) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
        <div className="rounded-lg bg-white p-8">
          <Loading size="lg" />
        </div>
      </div>
    );
  }

  if (!policy) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 overflow-y-auto">
      <div className="w-full max-w-4xl m-4 rounded-lg bg-white shadow-xl">
        <div className="border-b border-gray-200 p-6">
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <div className="flex items-center gap-3 mb-2">
                <h2 className="text-2xl font-bold text-gray-900">{policy.name}</h2>
                <Badge variant={getStatusBadgeVariant(policy.status)}>
                  {policy.status}
                </Badge>
                <Badge variant="info">v{policy.version}</Badge>
              </div>
              <p className="text-gray-600">{policy.description}</p>
            </div>
            <button
              onClick={onClose}
              className="rounded-lg p-2 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>

        <div className="p-6 space-y-6">
          {/* Policy Info */}
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <p className="text-sm font-medium text-gray-600">Policy ID</p>
              <p className="mt-1 text-sm text-gray-900 font-mono">{policy.policy_id}</p>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-600">Created By</p>
              <p className="mt-1 text-sm text-gray-900">{policy.created_by}</p>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-600">Created At</p>
              <p className="mt-1 text-sm text-gray-900">
                {new Date(policy.created_at).toLocaleString()}
              </p>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-600">Updated At</p>
              <p className="mt-1 text-sm text-gray-900">
                {policy.updated_at
                  ? new Date(policy.updated_at).toLocaleString()
                  : "Never"}
              </p>
            </div>
          </div>

          {/* Policy Content */}
          <div>
            <p className="text-sm font-medium text-gray-600 mb-2">Policy Content</p>
            <pre className="rounded-lg bg-gray-50 p-4 text-sm overflow-x-auto">
              {JSON.stringify(policy.content, null, 2)}
            </pre>
          </div>

          {/* Version History */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <p className="text-sm font-medium text-gray-600">Version History</p>
              <Button
                size="sm"
                variant="secondary"
                onClick={() => setShowVersions(!showVersions)}
              >
                <History className="h-4 w-4" />
                {showVersions ? "Hide" : "Show"} Versions ({versions.length})
              </Button>
            </div>

            {showVersions && (
              <div className="rounded-lg border border-gray-200 overflow-hidden">
                <table className="w-full">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-600">
                        Version
                      </th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-600">
                        Status
                      </th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-600">
                        Created By
                      </th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-600">
                        Created At
                      </th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-600">
                        Actions
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200">
                    {versions.map((ver) => (
                      <tr key={ver.version} className="hover:bg-gray-50">
                        <td className="px-4 py-2">
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-medium text-gray-900">v{ver.version}</span>
                            {ver.version === policy.version && (
                              <Badge variant="info" className="text-xs">Current</Badge>
                            )}
                          </div>
                        </td>
                        <td className="px-4 py-2">
                          <Badge variant={getStatusBadgeVariant(ver.status)}>
                            {ver.status}
                          </Badge>
                        </td>
                        <td className="px-4 py-2 text-sm text-gray-600">
                          {ver.created_by}
                        </td>
                        <td className="px-4 py-2 text-sm text-gray-600">
                          {new Date(ver.created_at).toLocaleString()}
                        </td>
                        <td className="px-4 py-2">
                          <div className="flex gap-1">
                            {ver.status !== "ACTIVE" && (
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => handleActivate(ver.version)}
                                title="Activate this version"
                              >
                                <CheckCircle className="h-4 w-4 text-green-600" />
                              </Button>
                            )}
                            {ver.version !== policy.version && (
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => handleRollback(ver.version)}
                                title="Rollback to this version"
                              >
                                <RotateCcw className="h-4 w-4 text-blue-600" />
                              </Button>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>

        {/* Actions */}
        <div className="border-t border-gray-200 p-6 bg-gray-50">
          <div className="flex justify-between">
            <div className="flex gap-2">
              {policy.status === "DRAFT" && (
                <>
                  <Button variant="secondary" onClick={() => onEdit(policy)}>
                    <Edit className="h-4 w-4" />
                    Edit
                  </Button>
                  <Button variant="danger" onClick={handleDelete}>
                    <Trash2 className="h-4 w-4" />
                    Delete
                  </Button>
                </>
              )}
              {policy.status === "ACTIVE" && (
                <Button variant="secondary" onClick={handleArchive}>
                  <Archive className="h-4 w-4" />
                  Archive
                </Button>
              )}
            </div>
            <div className="flex gap-2">
              {policy.status === "DRAFT" && (
                <Button onClick={() => handleActivate()}>
                  <Play className="h-4 w-4" />
                  Activate
                </Button>
              )}
              <Button variant="secondary" onClick={onClose}>
                Close
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
