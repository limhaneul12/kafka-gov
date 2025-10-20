import { useState, useEffect } from "react";
import { toast } from "sonner";
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
  GitCompare,
  ChevronRight,
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
  target_environment: string;
  updated_at: string | null;
  activated_at: string | null;
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
  
  // Diff 상태
  const [showDiff, setShowDiff] = useState(false);
  const [diffBaseVersion, setDiffBaseVersion] = useState<number | null>(null);
  const [diffTargetVersion, setDiffTargetVersion] = useState<number | null>(null);

  useEffect(() => {
    if (isOpen && policyId) {
      loadPolicy();
      loadVersions();
      setShowVersions(autoShowVersions);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen, policyId, autoShowVersions]);

  const loadPolicy = async (preferActive = false) => {
    try {
      setLoading(true);
      let response;
      
      if (preferActive) {
        // ACTIVE 버전 시도
        console.log("Trying to load ACTIVE policy...");
        response = await fetch(`/api/v1/policies/${policyId}/active`);
        
        if (!response.ok) {
          if (response.status === 422) {
            // ACTIVE가 없으면 최신 버전으로 fallback
            console.log("No ACTIVE version, falling back to latest...");
            response = await fetch(`/api/v1/policies/${policyId}`);
          } else {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
          }
        }
      } else {
        // 최신 버전 조회
        console.log("Loading latest policy...");
        response = await fetch(`/api/v1/policies/${policyId}`);
      }
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const data = await response.json();
      console.log("Policy loaded:", data.policy);
      setPolicy(data.policy);
    } catch (error: any) {
      console.error("Failed to load policy:", error);
      toast.error('정책 로드 실패', {
        description: error.message
      });
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
      // Activate 후에는 ACTIVE 버전을 우선적으로 조회
      await loadPolicy(true);
      await loadVersions();
      onRefresh();
    } catch (error) {
      console.error("Failed to activate policy:", error);
      toast.error("Failed to activate policy");
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
      toast.error("Failed to archive policy");
    }
  };

  const handleDelete = async () => {
    if (!policy) return;
    if (!confirm(`Delete policy "${policy.name}"? This cannot be undone.`)) return;

    try {
      await policiesAPI.delete(policyId);
      onRefresh();
      onClose();
    } catch (error) {
      console.error("Failed to delete policy:", error);
      toast.error("Failed to delete policy. Only DRAFT policies can be deleted.");
    }
  };

  const handleDeleteAllVersions = async () => {
    if (!policy) return;
    if (
      !confirm(
        `정책 "${policy.name}"의 모든 버전을 삭제하시겠습니까?\n\n⚠️ 이 작업은 되돌릴 수 없으며, ACTIVE/ARCHIVED 포함 모든 버전이 삭제됩니다.`
      )
    )
      return;

    try {
      // 모든 버전 삭제 API 호출
      await fetch(`/api/v1/policies/${policyId}/all`, {
        method: "DELETE",
      });
      onRefresh();
      onClose();
    } catch (error) {
      console.error("Failed to delete all versions:", error);
      toast.error("정책 전체 삭제에 실패했습니다.");
    }
  };

  const handleDeleteVersion = async (version: number) => {
    const versionData = versions.find((v) => v.version === version);
    if (!versionData) return;

    if (versionData.status === "ACTIVE") {
      toast.error("ACTIVE 상태의 버전은 삭제할 수 없습니다.");
      return;
    }

    if (
      !confirm(
        `v${version}을 삭제하시겠습니까?\n\n이 작업은 되돌릴 수 없습니다.`
      )
    )
      return;

    try {
      await fetch(`/api/v1/policies/${policyId}?version=${version}`, {
        method: "DELETE",
      });
      await loadPolicy();
      await loadVersions();
      onRefresh();
    } catch (error) {
      console.error("Failed to delete version:", error);
      toast.error("버전 삭제에 실패했습니다.");
    }
  };

  const handleRollback = async (targetVersion: number) => {
    // Toast 경고
    toast.warning(`v${targetVersion}으로 롤백`, {
      description: "롤백 버튼을 다시 한번 클릭하면 해당 버전이 ACTIVE로 변경됩니다.",
      duration: 5000,
    });

    try {
      const response = await fetch(`/api/v1/policies/${policyId}/rollback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          target_version: targetVersion,
          created_by: "admin@example.com",
        }),
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      // 롤백 후에는 ACTIVE 버전을 우선적으로 조회
      await loadPolicy(true);
      await loadVersions();
      onRefresh();
      toast.success("롤백 성공", {
        description: `v${targetVersion}으로 롤백되었습니다.`
      });
    } catch (error) {
      console.error("Failed to rollback policy:", error);
      toast.error("롤백 실패", {
        description: error instanceof Error ? error.message : "다시 시도해주세요."
      });
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

  // Diff 계산 함수
  const calculateDiff = (v1: number, v2: number) => {
    const version1 = versions.find(v => v.version === v1);
    const version2 = versions.find(v => v.version === v2);
    
    if (!version1 || !version2) return null;

    const content1 = version1.content;
    const content2 = version2.content;

    const diff: {
      added: Array<{ key: string; value: any }>;
      removed: Array<{ key: string; value: any }>;
      changed: Array<{ key: string; old: any; new: any }>;
    } = {
      added: [],
      removed: [],
      changed: [],
    };

    const allKeys = new Set([
      ...Object.keys(content1),
      ...Object.keys(content2),
    ]);

    allKeys.forEach(key => {
      const val1 = content1[key];
      const val2 = content2[key];

      if (val1 === undefined && val2 !== undefined) {
        diff.added.push({ key, value: val2 });
      } else if (val1 !== undefined && val2 === undefined) {
        diff.removed.push({ key, value: val1 });
      } else if (JSON.stringify(val1) !== JSON.stringify(val2)) {
        diff.changed.push({ key, old: val1, new: val2 });
      }
    });

    return diff;
  };

  const diffResult = (diffBaseVersion && diffTargetVersion) 
    ? calculateDiff(diffBaseVersion, diffTargetVersion)
    : null;

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
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 overflow-y-auto p-4">
      <div className="w-full max-w-5xl my-8 rounded-lg bg-white shadow-xl max-h-[90vh] overflow-y-auto">
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
              <p className="text-sm font-medium text-gray-600">Target Environment</p>
              <div className="mt-1">
                <Badge variant={policy.target_environment === "total" ? "default" : "warning"}>
                  {policy.target_environment}
                </Badge>
              </div>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-600">Policy Type</p>
              <div className="mt-1">
                <Badge variant="info">{policy.policy_type}</Badge>
              </div>
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
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm font-medium text-gray-600">Policy Content</p>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => onEdit(policy)}
                title={policy.status === "ACTIVE" ? "새 버전 생성" : "정책 수정"}
              >
                <Edit className="h-4 w-4" />
                {policy.status === "ACTIVE" ? "Edit (New Version)" : "Edit"}
              </Button>
            </div>
            <pre className="rounded-lg bg-gray-50 p-4 text-sm overflow-x-auto">
              {JSON.stringify(policy.content, null, 2)}
            </pre>
          </div>

          {/* Version History */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <p className="text-sm font-medium text-gray-600">Version History</p>
              <div className="flex gap-2">
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() => {
                    setShowDiff(!showDiff);
                    if (!showDiff) {
                      setShowVersions(true);
                      setDiffBaseVersion(null);
                      setDiffTargetVersion(null);
                    }
                  }}
                >
                  <GitCompare className="h-4 w-4" />
                  {showDiff ? "Hide" : "Compare"} Versions
                </Button>
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() => setShowVersions(!showVersions)}
                >
                  <History className="h-4 w-4" />
                  {showVersions ? "Hide" : "Show"} Versions ({versions.length})
                </Button>
              </div>
            </div>

            {/* Diff UI */}
            {showDiff && (
              <div className="mb-4 p-4 bg-gray-50 rounded-lg border border-gray-200">
                <h4 className="text-sm font-semibold text-gray-900 mb-3">
                  비교할 버전 선택
                </h4>
                <div className="grid grid-cols-3 gap-3 items-center">
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">
                      이전 버전 (Base)
                    </label>
                    <select
                      value={diffBaseVersion || ""}
                      onChange={(e) => setDiffBaseVersion(e.target.value ? Number(e.target.value) : null)}
                      className="w-full text-sm rounded border border-gray-300 px-3 py-2"
                    >
                      <option value="">선택하세요</option>
                      {versions.map(v => (
                        <option key={v.version} value={v.version}>
                          v{v.version} ({v.status})
                        </option>
                      ))}
                    </select>
                  </div>
                  
                  <div className="text-center">
                    <ChevronRight className="h-5 w-5 text-gray-400 mx-auto" />
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">
                      이후 버전 (Target)
                    </label>
                    <select
                      value={diffTargetVersion || ""}
                      onChange={(e) => setDiffTargetVersion(e.target.value ? Number(e.target.value) : null)}
                      className="w-full text-sm rounded border border-gray-300 px-3 py-2"
                    >
                      <option value="">선택하세요</option>
                      {versions.map(v => (
                        <option key={v.version} value={v.version}>
                          v{v.version} ({v.status})
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                {/* Diff 결과 */}
                {diffResult && (
                  <div className="mt-4 space-y-3">
                    <div className="flex items-center justify-between">
                      <h5 className="text-sm font-semibold text-gray-900">
                        비교 결과: v{diffBaseVersion} → v{diffTargetVersion}
                      </h5>
                      <div className="flex gap-3 text-xs">
                        <span className="text-green-700">+ {diffResult.added.length} 추가</span>
                        <span className="text-red-700">- {diffResult.removed.length} 삭제</span>
                        <span className="text-blue-700">~ {diffResult.changed.length} 변경</span>
                      </div>
                    </div>

                    <div className="border border-gray-200 rounded-lg overflow-hidden">
                      {/* 추가된 항목 */}
                      {diffResult.added.length > 0 && (
                        <div className="bg-green-50 border-b border-green-200">
                          <div className="px-3 py-2 bg-green-100 border-b border-green-200">
                            <span className="text-xs font-semibold text-green-900">
                              ✚ 추가됨 ({diffResult.added.length})
                            </span>
                          </div>
                          {diffResult.added.map(({ key, value }) => (
                            <div key={key} className="px-3 py-2 font-mono text-xs">
                              <span className="text-green-700 font-semibold">+ {key}:</span>{" "}
                              <span className="text-green-800">{JSON.stringify(value)}</span>
                            </div>
                          ))}
                        </div>
                      )}

                      {/* 삭제된 항목 */}
                      {diffResult.removed.length > 0 && (
                        <div className="bg-red-50 border-b border-red-200">
                          <div className="px-3 py-2 bg-red-100 border-b border-red-200">
                            <span className="text-xs font-semibold text-red-900">
                              ✖ 삭제됨 ({diffResult.removed.length})
                            </span>
                          </div>
                          {diffResult.removed.map(({ key, value }) => (
                            <div key={key} className="px-3 py-2 font-mono text-xs">
                              <span className="text-red-700 font-semibold">- {key}:</span>{" "}
                              <span className="text-red-800">{JSON.stringify(value)}</span>
                            </div>
                          ))}
                        </div>
                      )}

                      {/* 변경된 항목 */}
                      {diffResult.changed.length > 0 && (
                        <div className="bg-blue-50">
                          <div className="px-3 py-2 bg-blue-100 border-b border-blue-200">
                            <span className="text-xs font-semibold text-blue-900">
                              ⟳ 변경됨 ({diffResult.changed.length})
                            </span>
                          </div>
                          {diffResult.changed.map(({ key, old, new: newVal }) => (
                            <div key={key} className="px-3 py-2 space-y-1">
                              <div className="font-mono text-xs">
                                <span className="text-blue-700 font-semibold">~ {key}:</span>
                              </div>
                              <div className="ml-4 space-y-1">
                                <div className="font-mono text-xs">
                                  <span className="text-red-700">- </span>
                                  <span className="text-red-800 line-through">{JSON.stringify(old)}</span>
                                </div>
                                <div className="font-mono text-xs">
                                  <span className="text-green-700">+ </span>
                                  <span className="text-green-800">{JSON.stringify(newVal)}</span>
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>

                    {diffResult.added.length === 0 && 
                     diffResult.removed.length === 0 && 
                     diffResult.changed.length === 0 && (
                      <div className="text-center py-4 text-sm text-gray-500">
                        두 버전이 동일합니다
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            {showVersions && (
              <div className="rounded-lg border border-gray-200 overflow-hidden">
                <table className="w-full">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-600 w-20">
                        Version
                      </th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-600 w-24">
                        Status
                      </th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-600 w-40">
                        Created By
                      </th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-600 w-36">
                        Created At
                      </th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-600 w-36">
                        Using At
                      </th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-600 w-36">
                        Actions
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200">
                    {versions.map((ver) => (
                      <tr 
                        key={ver.version} 
                        className={`hover:bg-gray-50 ${ver.status === "ACTIVE" ? "bg-green-50" : ""}`}
                      >
                        <td className="px-4 py-2">
                          <div className="flex items-center gap-2">
                            <span className={`text-sm font-medium ${ver.status === "ACTIVE" ? "text-green-700" : "text-gray-900"}`}>
                              v{ver.version}
                            </span>
                            {ver.status === "ACTIVE" && (
                              <Badge variant="success" className="text-xs">적용중</Badge>
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
                        <td className="px-4 py-2 text-sm text-gray-600">
                          {ver.activated_at ? new Date(ver.activated_at).toLocaleString() : '-'}
                        </td>
                        <td className="px-4 py-2">
                          <div className="flex gap-1">
                            {ver.status !== "ACTIVE" && ver.status === "DRAFT" && (
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => handleActivate(ver.version)}
                                title="이 버전을 활성화"
                              >
                                <CheckCircle className="h-4 w-4 text-green-600" />
                              </Button>
                            )}
                            {ver.status !== "ACTIVE" && (
                              <>
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  onClick={() => handleRollback(ver.version)}
                                  title={`v${ver.version}을 ACTIVE로 변경`}
                                >
                                  <RotateCcw className="h-4 w-4 text-blue-600" />
                                </Button>
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  onClick={() => handleDeleteVersion(ver.version)}
                                  title={`v${ver.version} 삭제`}
                                >
                                  <Trash2 className="h-4 w-4 text-red-600" />
                                </Button>
                              </>
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
                <>
                  <Button variant="secondary" onClick={() => onEdit(policy)}>
                    <Edit className="h-4 w-4" />
                    Edit (Create New Version)
                  </Button>
                  <Button variant="secondary" onClick={handleArchive}>
                    <Archive className="h-4 w-4" />
                    Archive
                  </Button>
                </>
              )}
              {/* 정책 전체 삭제 버튼 */}
              <Button 
                variant="danger" 
                onClick={handleDeleteAllVersions}
                className="ml-auto"
              >
                <Trash2 className="h-4 w-4" />
                Delete All Versions
              </Button>
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
