import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import Loading from "../../../../../components/ui/Loading";
import { policiesAPI } from "../../../../../services/api";
import { PolicyHeader } from "./PolicyHeader";
import { PolicyContentView } from "./PolicyContentView";
import { PolicyVersionList } from "./PolicyVersionList";
import type { PolicyDetailModalProps, PolicyVersion } from "../../../Policies.types";

export function PolicyDetailModal({
  isOpen,
  onClose,
  policyId,
  onEdit,
  onRefresh,
  autoShowVersions = false,
}: PolicyDetailModalProps) {
  const { t } = useTranslation();
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
  }, [isOpen, policyId, autoShowVersions]);

  const loadPolicy = async () => {
    try {
      setLoading(true);
      const response = await fetch(`/api/v1/policies/${policyId}`);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      
      const data = await response.json();
      setPolicy(data);
    } catch (error) {
      console.error("Failed to load policy:", error);
      toast.error(t("error.general"));
    } finally {
      setLoading(false);
    }
  };

  const loadVersions = async () => {
    try {
      const response = await fetch(`/api/v1/policies/${policyId}/versions`);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      
      const data = await response.json();
      setVersions(data.versions || []);
    } catch (error) {
      console.error("Failed to load versions:", error);
    }
  };

  const handleVersionSelect = (version: PolicyVersion) => {
    setPolicy(version);
  };

  const handleActivate = async (policyId: string, version: number) => {
    try {
      await policiesAPI.activate(policyId, version);
      toast.success(t("policy.activate"));
      await loadPolicy();
      await loadVersions();
      onRefresh();
    } catch (error) {
      console.error("Failed to activate policy:", error);
      toast.error(t("error.general"));
    }
  };

  const handleArchive = async (policyId: string, version: number) => {
    try {
      await policiesAPI.archive(policyId, version);
      toast.success(t("policy.archive"));
      await loadPolicy();
      await loadVersions();
      onRefresh();
    } catch (error) {
      console.error("Failed to archive policy:", error);
      toast.error(t("error.general"));
    }
  };

  const handleDelete = async (policyId: string, version: number) => {
    if (!confirm(`Delete version ${version}?`)) return;

    try {
      await policiesAPI.deleteVersion(policyId, version);
      toast.success(t("common.success"));
      await loadVersions();
      onRefresh();
    } catch (error) {
      console.error("Failed to delete version:", error);
      toast.error(t("error.general"));
    }
  };

  const handleCompare = (version: number) => {
    // TODO: Implement version comparison
    console.log("Compare with version:", version);
    toast.info("Version comparison coming soon!");
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-40 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-6xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {loading ? (
          <div className="flex items-center justify-center h-96">
            <Loading size="lg" />
          </div>
        ) : policy ? (
          <>
            <PolicyHeader
              policy={policy}
              onEdit={() => onEdit(policy)}
              onClose={onClose}
              onToggleVersions={() => setShowVersions(!showVersions)}
              showVersions={showVersions}
            />

            <div className="flex-1 overflow-y-auto">
              <div className={`grid ${showVersions ? "grid-cols-2" : "grid-cols-1"} divide-x`}>
                {/* Main Content */}
                <div className="p-6">
                  <PolicyContentView policy={policy} />
                </div>

                {/* Version List */}
                {showVersions && (
                  <div className="p-6 bg-gray-50">
                    <PolicyVersionList
                      versions={versions}
                      currentVersion={policy.version}
                      onVersionSelect={handleVersionSelect}
                      onActivate={handleActivate}
                      onArchive={handleArchive}
                      onDelete={handleDelete}
                      onCompare={handleCompare}
                    />
                  </div>
                )}
              </div>
            </div>
          </>
        ) : (
          <div className="p-6 text-center text-gray-500">
            Policy not found
          </div>
        )}
      </div>
    </div>
  );
}
