import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/Card";
import Button from "../components/ui/Button";
import Badge from "../components/ui/Badge";
import Loading from "../components/ui/Loading";
import PolicyEditorModal from "../components/policy/PolicyEditorModal";
import PolicyDetailModal from "../components/policy/PolicyDetailModal";
import { policiesAPI } from "../services/api";
import { Plus, RefreshCw, Shield, Eye, Filter, Trash2, Edit } from "lucide-react";
import type { Policy } from "../types";

export default function Policies() {
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [loading, setLoading] = useState(true);
  const [showEditorModal, setShowEditorModal] = useState(false);
  const [showDetailModal, setShowDetailModal] = useState(false);
  const [selectedPolicyId, setSelectedPolicyId] = useState<string | null>(null);
  const [editingPolicy, setEditingPolicy] = useState<Policy | null>(null);
  const [editorMode, setEditorMode] = useState<"create" | "edit">("create");
  const [typeFilter, setTypeFilter] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<string>("");

  useEffect(() => {
    loadPolicies();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [typeFilter, statusFilter]);

  const loadPolicies = async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams();
      if (typeFilter) params.append("policy_type", typeFilter);
      if (statusFilter) params.append("status", statusFilter);
      
      const url = `/api/v1/policies${params.toString() ? `?${params.toString()}` : ""}`;
      const response = await fetch(url);
      const data = await response.json();
      setPolicies(data.policies || []);
    } catch (error) {
      console.error("Failed to load policies:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleCreatePolicy = async (data: {
    policy_type: string;
    name: string;
    description: string;
    content: Record<string, unknown>;
    created_by: string;
    target_environment?: string;
  }) => {
    await policiesAPI.create(data);
    await loadPolicies();
  };

  const handleUpdatePolicy = async (data: {
    name?: string;
    description?: string;
    content?: Record<string, unknown>;
  }) => {
    if (!selectedPolicyId) return;
    await policiesAPI.update(selectedPolicyId, data);
    await loadPolicies();
  };

  const handleDeletePolicy = async (policyId: string, policyName: string) => {
    if (!confirm(`Delete policy "${policyName}"? This action cannot be undone.`)) {
      return;
    }

    try {
      await policiesAPI.delete(policyId);
      await loadPolicies();
    } catch (error) {
      console.error("Failed to delete policy:", error);
      alert("Failed to delete policy. Only DRAFT policies can be deleted.");
    }
  };

  const handleViewPolicy = (policyId: string) => {
    setSelectedPolicyId(policyId);
    setShowDetailModal(true);
  };

  const handleEditFromDetail = (policy: Policy) => {
    setEditingPolicy(policy);
    setSelectedPolicyId(policy.policy_id);
    setEditorMode("edit");
    setShowDetailModal(false);
    setShowEditorModal(true);
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

  if (loading) {
    return (
      <div className="flex h-96 items-center justify-center">
        <Loading size="lg" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Policies</h1>
          <p className="mt-2 text-gray-600">토픽 정책을 생성하고 버전을 관리합니다</p>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={loadPolicies}>
            <RefreshCw className="h-4 w-4" />
            Refresh
          </Button>
          <Button
            onClick={() => {
              setEditorMode("create");
              setEditingPolicy(null);
              setShowEditorModal(true);
            }}
          >
            <Plus className="h-4 w-4" />
            Create Policy
          </Button>
        </div>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center gap-4">
            <Filter className="h-5 w-5 text-gray-400" />
            <div className="grid gap-4 md:grid-cols-3 flex-1">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Policy Type
                </label>
                <select
                  value={typeFilter}
                  onChange={(e) => setTypeFilter(e.target.value)}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                >
                  <option value="">All Types</option>
                  <option value="naming">Naming</option>
                  <option value="guardrail">Guardrail</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Status
                </label>
                <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                >
                  <option value="">All Status</option>
                  <option value="DRAFT">Draft</option>
                  <option value="ACTIVE">Active</option>
                  <option value="ARCHIVED">Archived</option>
                </select>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5" />
            Policies ({policies.length})
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">
                    Name
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">
                    Type
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">
                    Version
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">
                    Status
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">
                    Created By
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">
                    Updated
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {policies.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-4 py-8 text-center text-gray-500">
                      No policies found
                    </td>
                  </tr>
                ) : (
                  policies.map((policy) => (
                    <tr key={policy.policy_id} className="hover:bg-gray-50">
                      <td className="px-4 py-3 text-sm font-medium text-gray-900">
                        {policy.name}
                      </td>
                      <td className="px-4 py-3">
                        <Badge variant="info">{policy.policy_type}</Badge>
                      </td>
                      <td className="px-4 py-3">
                        <button
                          onClick={() => handleViewPolicy(policy.policy_id)}
                          className="flex items-center gap-1 text-sm text-blue-600 hover:text-blue-800 hover:underline"
                          title="View version history"
                        >
                          <Eye className="h-3 w-3" />
                          v{policy.version}
                        </button>
                      </td>
                      <td className="px-4 py-3">
                        <Badge variant={getStatusBadgeVariant(policy.status)}>
                          {policy.status}
                        </Badge>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600">
                        {policy.created_by}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600">
                        {policy.updated_at
                          ? new Date(policy.updated_at).toLocaleDateString()
                          : "-"}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex gap-1">
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => handleViewPolicy(policy.policy_id)}
                            title="View Details"
                          >
                            <Eye className="h-4 w-4 text-blue-600" />
                          </Button>
                          {policy.status?.toUpperCase() === "DRAFT" && (
                            <>
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => {
                                  setEditingPolicy(policy);
                                  setEditorMode("edit");
                                  setShowEditorModal(true);
                                }}
                                title="Edit Policy"
                              >
                                <Edit className="h-4 w-4 text-blue-600" />
                              </Button>
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => handleDeletePolicy(policy.policy_id, policy.name)}
                                title="Delete Policy"
                              >
                                <Trash2 className="h-4 w-4 text-red-600" />
                              </Button>
                            </>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Modals */}
      <PolicyEditorModal
        isOpen={showEditorModal}
        onClose={() => {
          setShowEditorModal(false);
          setEditingPolicy(null);
        }}
        onSubmit={editorMode === "create" ? handleCreatePolicy : handleUpdatePolicy}
        initialData={editingPolicy}
        mode={editorMode}
      />

      {selectedPolicyId && (
        <PolicyDetailModal
          isOpen={showDetailModal}
          onClose={() => {
            setShowDetailModal(false);
            setSelectedPolicyId(null);
          }}
          policyId={selectedPolicyId}
          onEdit={handleEditFromDetail}
          onRefresh={loadPolicies}
        />
      )}
    </div>
  );
}
