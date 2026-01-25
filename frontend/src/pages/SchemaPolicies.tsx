import { useState, useEffect, useCallback } from "react";
import { toast } from "sonner";
import { Plus, RefreshCw, Layers } from "lucide-react";

import { Card, CardHeader, CardTitle, CardContent } from "../components/ui/Card";
import Button from "../components/ui/Button";
import schemaApi from "../services/schemaApi";

// New specialized components
import SchemaPolicyList from "../components/schema/policies/SchemaPolicyList";
import SchemaPolicyDetailModal from "../components/schema/policies/SchemaPolicyDetailModal";
import SchemaPolicyComposer from "../components/schema/policies/SchemaPolicyComposer";

export default function SchemaPolicies() {
  const [policies, setPolicies] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  // Modals state
  const [selectedPolicy, setSelectedPolicy] = useState<any | null>(null);
  const [policyHistory, setPolicyHistory] = useState<any[]>([]);
  const [isDetailOpen, setIsDetailOpen] = useState(false);
  const [isComposerOpen, setIsComposerOpen] = useState(false);

  // 1. Data Loading (Minimal useEffect)
  const fetchPolicies = useCallback(async () => {
    try {
      setLoading(true);
      const data = await schemaApi.listPolicies();
      setPolicies(data);
    } catch (err) {
      toast.error("Failed to load schema policies");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPolicies();
  }, [fetchPolicies]);

  // 2. Action Handlers
  const handleViewDetail = async (policy: any) => {
    setSelectedPolicy(policy);
    setIsDetailOpen(true);
    try {
      const history = await schemaApi.getPolicyHistory(policy.policy_id);
      setPolicyHistory(history);
    } catch (err) {
      toast.error("Failed to load policy history");
    }
  };

  const handleActivate = async (policy: any) => {
    try {
      await schemaApi.updatePolicyStatus(policy.policy_id, policy.version, "active");
      toast.success(`Policy ${policy.name} v${policy.version} is now ACTIVE`);
      fetchPolicies();
    } catch (err) {
      toast.error("Failed to activate policy");
    }
  };

  const handleCreateSubmit = async (data: any) => {
    try {
      await schemaApi.createPolicy(data);
      toast.success("Policy created successfully (as DRAFT)");
      fetchPolicies();
    } catch (err) {
      toast.error("Failed to create policy");
      throw err; // Composer will handle loading state
    }
  };

  const handleRollback = async (version: number) => {
    if (!selectedPolicy) return;
    try {
      await schemaApi.updatePolicyStatus(selectedPolicy.policy_id, version, "active");
      toast.success(`Success! Rolled back to v${version}`);
      setIsDetailOpen(false);
      fetchPolicies();
    } catch (err) {
      toast.error("Failed to rollback version");
    }
  };

  return (
    <div className="space-y-6 max-w-[1200px] mx-auto pb-20">
      {/* Page Header */}
      <div className="flex items-end justify-between">
        <div>
          <div className="flex items-center gap-2 text-blue-600 font-semibold text-sm mb-1">
            <Layers className="h-4 w-4" />
            Governance Engine
          </div>
          <h1 className="text-3xl font-bold text-gray-900 tracking-tight">Schema Policies</h1>
          <p className="mt-1 text-sm text-gray-500">
            Customize linting rules and environment guardrails for schema evolution
          </p>
        </div>
        <div className="flex gap-2 mb-1">
          <Button onClick={fetchPolicies} variant="ghost" size="sm" disabled={loading}>
            <RefreshCw className={`h-4 w-4 mr-2 ${loading ? "animate-spin" : ""}`} />
            Sync
          </Button>
          <Button onClick={() => setIsComposerOpen(true)}>
            <Plus className="h-4 w-4 mr-2" />
            New Policy
          </Button>
        </div>
      </div>

      {/* Stats Quick View (Optionally could be a separate component if more complex) */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="bg-gradient-to-br from-blue-600 to-blue-700 text-white border-none shadow-blue-100">
          <CardContent className="pt-6">
            <div className="text-sm font-medium opacity-80">Total Policies</div>
            <div className="text-3xl font-bold mt-1">{policies.length}</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-sm font-medium text-gray-500">Active</div>
            <div className="text-3xl font-bold mt-1 text-green-600">
              {policies.filter(p => p.status === "active").length}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Policy List Container */}
      <Card className="overflow-hidden border-gray-200 shadow-sm">
        <CardHeader className="bg-white border-b border-gray-100">
          <CardTitle className="text-lg font-bold">Policy Inventory</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <SchemaPolicyList
            policies={policies}
            loading={loading}
            onViewDetail={handleViewDetail}
            onViewHistory={handleViewDetail} // Detail modal has history sidebar
            onActivate={handleActivate}
          />
        </CardContent>
      </Card>

      {/* Modals (Lazy-ish mounting via isOpen check inside components) */}
      <SchemaPolicyDetailModal
        isOpen={isDetailOpen}
        onClose={() => setIsDetailOpen(false)}
        policy={selectedPolicy}
        history={policyHistory}
        onActivateVersion={handleRollback}
      />

      <SchemaPolicyComposer
        isOpen={isComposerOpen}
        onClose={() => setIsComposerOpen(false)}
        onSubmit={handleCreateSubmit}
      />
    </div>
  );
}
