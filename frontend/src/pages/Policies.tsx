import { useEffect, useState } from "react";
import { toast } from "sonner";
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
  const [activeTab, setActiveTab] = useState<"naming" | "guardrail">("naming");
  const [statusFilter, setStatusFilter] = useState<string>("");

  useEffect(() => {
    loadPolicies();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab, statusFilter]);

  const loadPolicies = async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams();
      params.append("policy_type", activeTab);
      if (statusFilter) params.append("status", statusFilter);
      
      const url = `/api/v1/policies?${params.toString()}`;
      console.log("Loading policies from:", url);
      const response = await fetch(url);
      
      if (!response.ok) {
        console.error("API Error:", response.status, response.statusText);
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      console.log("Received data:", data);
      setPolicies(data.policies || []);
    } catch (error) {
      console.error("Failed to load policies:", error);
      setPolicies([]);
      toast.error('정책 로드 실패', {
        description: error instanceof Error ? error.message : '알 수 없는 오류가 발생했습니다.'
      });
    } finally {
      setLoading(false);
    }
  };

  const handleCreatePolicy = async (data: {
    policy_type?: string;
    name: string;
    description: string;
    content: Record<string, unknown>;
    created_by?: string;
    target_environment?: string;
  }) => {
    // Create 모드에서만 호출되므로 필수 필드 확인
    if (!data.policy_type || !data.created_by) {
      toast.warning('필수 필드 누락', {
        description: 'Policy type과 created_by는 필수입니다.'
      });
      return;
    }
    
    try {
      await policiesAPI.create(data as {
        policy_type: string;
        name: string;
        description: string;
        content: Record<string, unknown>;
        created_by: string;
        target_environment?: string;
      });
      await loadPolicies();
      toast.success('생성 성공', {
        description: '정책이 성공적으로 생성되었습니다.'
      });
    } catch (error: unknown) {
      toast.error('정책 생성 실패', {
        description: error instanceof Error ? error.message : '알 수 없는 오류가 발생했습니다.'
      });
    }
  };

  const handleUpdatePolicy = async (data: {
    policy_type?: string;
    name: string;
    description: string;
    content: Record<string, unknown>;
    created_by?: string;
    target_environment?: string;
  }) => {
    if (!selectedPolicyId) {
      console.error("No policy selected for update");
      toast.warning('선택 필요', {
        description: '수정할 정책을 선택하세요.'
      });
      return;
    }
    
    try {
      console.log("Updating policy:", selectedPolicyId, data);
      // Edit 모드: name, description, content, target_environment 전송
      await policiesAPI.update(selectedPolicyId, {
        name: data.name,
        description: data.description,
        content: data.content,
        target_environment: data.target_environment,
      });
      await loadPolicies();
      toast.success('수정 완료', {
        description: '정책이 성공적으로 업데이트되었습니다.'
      });
    } catch (error) {
      toast.error('정책 수정 실패', {
        description: error instanceof Error ? error.message : '알 수 없는 오류가 발생했습니다.'
      });
      throw error;
    }
  };

  const handleDeletePolicy = async (policyId: string, policyName: string) => {
    // Toast 경고 (삭제는 위험하므로 경고만 표시)
    toast.warning(`정책 "${policyName}" 삭제`, {
      description: "삭제 버튼을 다시 한번 클릭하면 완전히 삭제됩니다.",
      duration: 5000,
    });

    try {
      await policiesAPI.delete(policyId);
      await loadPolicies();
      toast.success('삭제 완료', {
        description: '정책이 삭제되었습니다.'
      });
    } catch (error) {
      toast.error('정책 삭제 실패', {
        description: error instanceof Error ? error.message : '알 수 없는 오류가 발생했습니다.'
      });
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
            Create {activeTab === "naming" ? "Naming" : "Guardrail"} Policy
          </Button>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-8">
          <button
            onClick={() => setActiveTab("naming")}
            className={`${
              activeTab === "naming"
                ? "border-blue-500 text-blue-600"
                : "border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700"
            } whitespace-nowrap border-b-2 py-4 px-1 text-sm font-medium transition-colors`}
          >
            <div className="flex items-center gap-2">
              <Shield className="h-4 w-4" />
              Topic Naming Policy
            </div>
          </button>
          <button
            onClick={() => setActiveTab("guardrail")}
            className={`${
              activeTab === "guardrail"
                ? "border-blue-500 text-blue-600"
                : "border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700"
            } whitespace-nowrap border-b-2 py-4 px-1 text-sm font-medium transition-colors`}
          >
            <div className="flex items-center gap-2">
              <Shield className="h-4 w-4" />
              Topic Creation Guardrails
            </div>
          </button>
        </nav>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <Shield className="h-5 w-5" />
              {activeTab === "naming" ? "Naming Policies" : "Guardrail Policies"} ({policies.length})
            </CardTitle>
            <div className="flex items-center gap-2">
              <Filter className="h-4 w-4 text-gray-400" />
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="text-sm rounded-lg border border-gray-300 px-3 py-1.5 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                <option value="">All Status</option>
                <option value="DRAFT">Draft</option>
                <option value="ACTIVE">Active</option>
                <option value="ARCHIVED">Archived</option>
              </select>
            </div>
          </div>
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
                    적용 버전
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">
                    작성된 버전
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">
                    Status
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">
                    Environment
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
                    <td colSpan={7} className="px-4 py-12 text-center">
                      <div className="flex flex-col items-center gap-3">
                        <Shield className="h-12 w-12 text-gray-300" />
                        <p className="text-gray-500 font-medium">
                          No {activeTab === "naming" ? "naming" : "guardrail"} policies found
                        </p>
                        <p className="text-sm text-gray-400">
                          Create your first {activeTab} policy to get started
                        </p>
                      </div>
                    </td>
                  </tr>
                ) : (
                  policies.map((policy) => (
                    <tr key={policy.policy_id} className="hover:bg-gray-50">
                      <td className="px-4 py-3 text-sm font-medium text-gray-900">
                        {policy.name}
                      </td>
                      <td className="px-4 py-3">
                        {policy.status.toUpperCase() === "ACTIVE" ? (
                          <span className="text-sm font-medium text-green-600">
                            v{policy.version}
                          </span>
                        ) : (
                          <span className="text-sm text-gray-400">-</span>
                        )}
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
                      <td className="px-4 py-3">
                        <Badge variant={policy.target_environment === "total" ? "default" : "warning"}>
                          {policy.target_environment}
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
                                  setSelectedPolicyId(policy.policy_id);
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
          setSelectedPolicyId(null);
        }}
        onSubmit={editorMode === "create" ? handleCreatePolicy : handleUpdatePolicy}
        initialData={editingPolicy}
        mode={editorMode}
        defaultPolicyType={activeTab}
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
