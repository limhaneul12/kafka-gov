import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/Card";
import Button from "../components/ui/Button";
import Badge from "../components/ui/Badge";
import Loading from "../components/ui/Loading";
import PolicyEditorModal from "../components/policy/PolicyEditorModal";
import PolicyDetailModal from "../components/policy/PolicyDetailModal";
import { Plus, RefreshCw, Shield, Eye, Filter, Trash2, Edit } from "lucide-react";
import type { Policy } from "../types";

export default function TopicPolicies() {
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [loading, setLoading] = useState(true);
  const [showEditorModal, setShowEditorModal] = useState(false);
  const [showDetailModal, setShowDetailModal] = useState(false);
  const [selectedPolicyId, setSelectedPolicyId] = useState<string | null>(null);
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
      const response = await fetch(url);
      
      if (!response.ok) {
        console.error("API Error:", response.status, response.statusText);
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      setPolicies(data.policies || []);
    } catch (error) {
      console.error("Failed to load topic policies:", error);
      setPolicies([]);
      toast.error("Failed to load topic policies");
    } finally {
      setLoading(false);
    }
  };

  const handleViewPolicy = (policyId: string) => {
    setSelectedPolicyId(policyId);
    setShowDetailModal(true);
  };

  const handleEditPolicy = (policy: Policy) => {
    setSelectedPolicyId(policy.policy_id);
    setEditorMode("edit");
    setShowEditorModal(true);
  };

  const handleCreateNew = () => {
    setSelectedPolicyId(null);
    setEditorMode("create");
    setShowEditorModal(true);
  };

  const handleDeletePolicy = async (policyId: string) => {
    if (!confirm("Are you sure you want to delete this policy?")) return;
    
    try {
      const response = await fetch(`/api/v1/policies/${policyId}`, {
        method: "DELETE",
      });
      
      if (!response.ok) throw new Error("Failed to delete policy");
      
      toast.success("Policy deleted successfully");
      loadPolicies();
    } catch (error) {
      console.error("Failed to delete policy:", error);
      toast.error("Failed to delete policy");
    }
  };

  if (loading) return <Loading />;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Topic Policies</h1>
          <p className="mt-1 text-sm text-gray-500">
            Manage naming conventions and guardrails for Kafka topics
          </p>
        </div>
        <div className="flex gap-2">
          <Button onClick={loadPolicies} variant="secondary">
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
          <Button onClick={handleCreateNew}>
            <Plus className="h-4 w-4 mr-2" />
            Create Policy
          </Button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-4 border-b border-gray-200">
        <button
          onClick={() => setActiveTab("naming")}
          className={`px-4 py-2 font-medium transition-colors border-b-2 ${
            activeTab === "naming"
              ? "border-blue-600 text-blue-600"
              : "border-transparent text-gray-500 hover:text-gray-700"
          }`}
        >
          <Shield className="h-4 w-4 inline mr-2" />
          Naming Rules
        </button>
        <button
          onClick={() => setActiveTab("guardrail")}
          className={`px-4 py-2 font-medium transition-colors border-b-2 ${
            activeTab === "guardrail"
              ? "border-blue-600 text-blue-600"
              : "border-transparent text-gray-500 hover:text-gray-700"
          }`}
        >
          <Shield className="h-4 w-4 inline mr-2" />
          Guardrails
        </button>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex gap-4 items-center">
            <Filter className="h-5 w-5 text-gray-400" />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              <option value="">All Status</option>
              <option value="active">Active</option>
              <option value="draft">Draft</option>
            </select>
          </div>
        </CardContent>
      </Card>

      {/* Policy List */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {policies.map((policy) => (
          <Card key={policy.policy_id} className="hover:shadow-md transition-shadow">
            <CardHeader>
              <div className="flex items-start justify-between">
                <CardTitle className="text-lg">{policy.name}</CardTitle>
                <Badge variant={policy.status === "ACTIVE" ? "success" : "warning"}>
                  {policy.status}
                </Badge>
              </div>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-gray-600 mb-4 line-clamp-2">
                {policy.description || "No description"}
              </p>
              <div className="flex gap-2">
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => handleViewPolicy(policy.policy_id)}
                >
                  <Eye className="h-4 w-4 mr-1" />
                  View
                </Button>
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => handleEditPolicy(policy)}
                >
                  <Edit className="h-4 w-4 mr-1" />
                  Edit
                </Button>
                <Button
                  variant="danger"
                  size="sm"
                  onClick={() => handleDeletePolicy(policy.policy_id)}
                >
                  <Trash2 className="h-4 w-4 mr-1" />
                  Delete
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {policies.length === 0 && (
        <Card>
          <CardContent className="text-center py-12">
            <Shield className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">No policies found</h3>
            <p className="text-sm text-gray-500 mb-4">
              Create your first topic policy to get started
            </p>
            <Button onClick={handleCreateNew}>
              <Plus className="h-4 w-4 mr-2" />
              Create Policy
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Modals */}
      {showEditorModal && (
        <PolicyEditorModal
          isOpen={showEditorModal}
          onClose={() => {
            setShowEditorModal(false);
            setSelectedPolicyId(null);
          }}
          mode={editorMode}
          defaultPolicyType={activeTab}
          onSubmit={async (data) => {
            try {
              const url = editorMode === "create" 
                ? "/api/v1/policies"
                : `/api/v1/policies/${selectedPolicyId}`;
              const method = editorMode === "create" ? "POST" : "PUT";
              
              const response = await fetch(url, {
                method,
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                  ...data,
                  policy_type: activeTab,
                }),
              });
              
              if (!response.ok) throw new Error("Failed to save policy");
              
              toast.success(`Policy ${editorMode === "create" ? "created" : "updated"} successfully`);
              loadPolicies();
              setShowEditorModal(false);
              setSelectedPolicyId(null);
            } catch (error) {
              console.error("Failed to save policy:", error);
              toast.error("Failed to save policy");
              throw error;
            }
          }}
        />
      )}

      {showDetailModal && selectedPolicyId && (
        <PolicyDetailModal
          isOpen={showDetailModal}
          onClose={() => {
            setShowDetailModal(false);
            setSelectedPolicyId(null);
          }}
          policyId={selectedPolicyId}
          onEdit={(policy) => {
            setSelectedPolicyId(policy.policy_id);
            setEditorMode("edit");
            setShowEditorModal(true);
            setShowDetailModal(false);
          }}
          onRefresh={loadPolicies}
        />
      )}
    </div>
  );
}
