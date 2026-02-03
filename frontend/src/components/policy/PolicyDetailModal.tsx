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
  GitCompare,
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
        response = await fetch(`/api/v1/policies/${policyId}/active`);

        if (!response.ok) {
          if (response.status === 422) {
            // ACTIVE가 없으면 최신 버전으로 fallback
            response = await fetch(`/api/v1/policies/${policyId}`);
          } else {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
          }
        }
      } else {
        // 최신 버전 조회
        response = await fetch(`/api/v1/policies/${policyId}`);
      }

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
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
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-70 p-4 backdrop-blur-sm">
      <div className="w-full max-w-5xl rounded-2xl bg-white shadow-2xl flex flex-col max-h-[92vh] border border-gray-100">
        {/* Header - Fixed */}
        <div className="border-b border-gray-100 p-6 flex-shrink-0 bg-white rounded-t-2xl">
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <div className="flex items-center gap-3 mb-2">
                <h2 className="text-2xl font-bold text-gray-900 tracking-tight">{policy.name}</h2>
                <Badge variant={getStatusBadgeVariant(policy.status)}>
                  {policy.status}
                </Badge>
                <Badge variant="info" className="font-mono">v{policy.version}</Badge>
              </div>
              <p className="text-gray-500 text-sm leading-relaxed">{policy.description}</p>
            </div>
            <button
              onClick={onClose}
              className="rounded-xl p-2.5 text-gray-400 hover:bg-gray-100 hover:text-gray-600 transition-colors"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>

        {/* Body - Scrollable */}
        <div className="p-6 space-y-8 flex-1 overflow-y-auto custom-scrollbar">
          {/* Policy Info */}
          <div className="grid gap-6 md:grid-cols-2 bg-gray-50 rounded-2xl p-6 border border-gray-100">
            <div className="space-y-1">
              <p className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">Policy ID</p>
              <p className="text-sm text-gray-900 font-mono bg-white px-2 py-1 rounded inline-block border border-gray-200">{policy.policy_id}</p>
            </div>
            <div className="space-y-1">
              <p className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">Created By</p>
              <p className="text-sm text-gray-900 flex items-center gap-2">
                <span className="w-6 h-6 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center text-[10px] font-bold">
                  {policy.created_by[0].toUpperCase()}
                </span>
                {policy.created_by}
              </p>
            </div>
            <div className="space-y-1">
              <p className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">Target Environment</p>
              <div className="mt-1">
                <Badge variant={policy.target_environment === "total" ? "default" : "warning"} className="font-semibold px-2">
                  {policy.target_environment.toUpperCase()}
                </Badge>
              </div>
            </div>
            <div className="space-y-1">
              <p className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">Policy Type</p>
              <div className="mt-1">
                <Badge variant="info" className="font-semibold px-2">{policy.policy_type}</Badge>
              </div>
            </div>
            <div className="space-y-1">
              <p className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">Created At</p>
              <p className="text-sm text-gray-600">
                {new Date(policy.created_at).toLocaleString()}
              </p>
            </div>
            <div className="space-y-1">
              <p className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">Updated At</p>
              <p className="text-sm text-gray-600">
                {policy.updated_at
                  ? new Date(policy.updated_at).toLocaleString()
                  : "Never"}
              </p>
            </div>
          </div>

          {/* Policy Content */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-gray-900 flex items-center gap-2">
                <Play className="h-4 w-4 text-blue-500 fill-blue-500" />
                POLICY CONFIGURATION
              </h3>
              <Button
                size="sm"
                variant="ghost"
                className="hover:bg-blue-50 text-blue-600"
                onClick={() => onEdit(policy)}
                title={policy.status === "ACTIVE" ? "새 버전 생성" : "정책 수정"}
              >
                <Edit className="h-3.5 w-3.5 mr-1" />
                {policy.status === "ACTIVE" ? "Create New Version" : "Edit"}
              </Button>
            </div>
            <div className="relative group">
              <pre className="rounded-2xl bg-gray-900 text-gray-100 p-6 text-sm overflow-x-auto font-mono leading-relaxed shadow-inner max-h-[400px]">
                {JSON.stringify(policy.content, null, 2)}
              </pre>
            </div>
          </div>

          {/* Version History Section */}
          <div className="space-y-4">
            <div className="flex items-center justify-between border-b border-gray-100 pb-3">
              <h3 className="text-sm font-bold text-gray-900 flex items-center gap-2">
                <History className="h-4 w-4 text-purple-500" />
                VERSION HISTORY
              </h3>
              <div className="flex gap-2">
                <Button
                  size="sm"
                  variant="secondary"
                  className="rounded-full h-8 text-xs px-4"
                  onClick={() => {
                    setShowDiff(!showDiff);
                    if (!showDiff) {
                      setShowVersions(true);
                      setDiffBaseVersion(null);
                      setDiffTargetVersion(null);
                    }
                  }}
                >
                  <GitCompare className="h-3.5 w-3.5 mr-1.5" />
                  {showDiff ? "Hide Comparison" : "Diff View"}
                </Button>
                <Button
                  size="sm"
                  variant="secondary"
                  className="rounded-full h-8 text-xs px-4"
                  onClick={() => setShowVersions(!showVersions)}
                >
                  <History className="h-3.5 w-3.5 mr-1.5" />
                  {showVersions ? "Hide Timeline" : "Show Full Timeline"}
                </Button>
              </div>
            </div>

            {/* Diff UI */}
            {showDiff && (
              <div className="animate-in fade-in slide-in-from-top-2 duration-300">
                <div className="p-5 bg-blue-50 rounded-2xl border border-blue-100">
                  <div className="grid grid-cols-2 gap-4 items-center">
                    <div className="space-y-1.5">
                      <label className="text-[10px] font-bold text-blue-600 uppercase tracking-wider ml-1">Base Version</label>
                      <select
                        value={diffBaseVersion || ""}
                        onChange={(e) => setDiffBaseVersion(e.target.value ? Number(e.target.value) : null)}
                        className="w-full text-sm rounded-xl border-blue-200 bg-white px-4 py-2.5 focus:ring-2 focus:ring-blue-500/20 transition-all outline-none"
                      >
                        <option value="">Select version...</option>
                        {versions.map(v => (
                          <option key={v.version} value={v.version}>
                            v{v.version} {v.status === 'ACTIVE' ? '🟢' : '⚪️'} {v.status}
                          </option>
                        ))}
                      </select>
                    </div>

                    <div className="space-y-1.5">
                      <label className="text-[10px] font-bold text-blue-600 uppercase tracking-wider ml-1">Target Version</label>
                      <select
                        value={diffTargetVersion || ""}
                        onChange={(e) => setDiffTargetVersion(e.target.value ? Number(e.target.value) : null)}
                        className="w-full text-sm rounded-xl border-blue-200 bg-white px-4 py-2.5 focus:ring-2 focus:ring-blue-500/20 transition-all outline-none"
                      >
                        <option value="">Select version...</option>
                        {versions.map(v => (
                          <option key={v.version} value={v.version}>
                            v{v.version} {v.status === 'ACTIVE' ? '🟢' : '⚪️'} {v.status}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>

                  {/* Diff Results */}
                  {diffResult && (
                    <div className="mt-5 space-y-4 animate-in zoom-in-95 duration-200">
                      <div className="flex items-center justify-between px-1">
                        <span className="text-xs font-bold text-blue-900 bg-blue-100/50 px-3 py-1 rounded-full">
                          v{diffBaseVersion} → v{diffTargetVersion}
                        </span>
                        <div className="flex gap-4">
                          <span className="text-[11px] font-bold text-green-600">+{diffResult.added.length}</span>
                          <span className="text-[11px] font-bold text-red-500">-{diffResult.removed.length}</span>
                          <span className="text-[11px] font-bold text-blue-500">~{diffResult.changed.length}</span>
                        </div>
                      </div>

                      <div className="bg-white rounded-xl border border-blue-100 overflow-hidden shadow-sm">
                        {/* Added Items */}
                        {diffResult.added.length > 0 && (
                          <div className="border-b border-blue-50">
                            <div className="px-4 py-2 bg-green-50/50 border-b border-green-100">
                              <span className="text-[10px] font-bold text-green-700 uppercase tracking-tight">Added</span>
                            </div>
                            {diffResult.added.map(({ key, value }) => (
                              <div key={key} className="px-4 py-2.5 font-mono text-xs border-b border-gray-50 last:border-0">
                                <span className="text-green-600 font-bold mr-2">+</span>
                                <span className="text-gray-900 font-semibold">{key}</span>:{" "}
                                <span className="text-gray-600 italic">{JSON.stringify(value)}</span>
                              </div>
                            ))}
                          </div>
                        )}

                        {/* Removed Items */}
                        {diffResult.removed.length > 0 && (
                          <div className="border-b border-blue-50">
                            <div className="px-4 py-2 bg-red-50/50 border-b border-red-100">
                              <span className="text-[10px] font-bold text-red-700 uppercase tracking-tight">Removed</span>
                            </div>
                            {diffResult.removed.map(({ key, value }) => (
                              <div key={key} className="px-4 py-2.5 font-mono text-xs border-b border-gray-50 last:border-0">
                                <span className="text-red-500 font-bold mr-2">-</span>
                                <span className="text-gray-400 line-through">{key}</span>:{" "}
                                <span className="text-gray-400 opacity-60">{JSON.stringify(value)}</span>
                              </div>
                            ))}
                          </div>
                        )}

                        {/* Changed Items */}
                        {diffResult.changed.length > 0 && (
                          <div>
                            <div className="px-4 py-2 bg-blue-50/50 border-b border-blue-100">
                              <span className="text-[10px] font-bold text-blue-700 uppercase tracking-tight">Changed</span>
                            </div>
                            {diffResult.changed.map(({ key, old, new: newVal }) => (
                              <div key={key} className="px-4 py-3 border-b border-gray-50 last:border-0">
                                <div className="font-mono text-xs mb-1.5 flex items-center gap-2">
                                  <span className="text-blue-500 font-bold">~</span>
                                  <span className="text-gray-900 font-bold">{key}</span>
                                </div>
                                <div className="ml-4 space-y-1">
                                  <div className="font-mono text-[11px] text-red-400/80 line-through">- {JSON.stringify(old)}</div>
                                  <div className="font-mono text-[11px] text-green-600 bg-green-50 px-1.5 py-0.5 rounded">+ {JSON.stringify(newVal)}</div>
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}

            {showVersions && (
              <div className="rounded-2xl border border-gray-100 overflow-hidden shadow-sm">
                <table className="w-full border-collapse">
                  <thead className="bg-gray-50/50 border-b border-gray-100">
                    <tr>
                      <th className="px-5 py-3 text-left text-[10px] font-bold text-gray-500 uppercase tracking-widest w-24">Version</th>
                      <th className="px-5 py-3 text-left text-[10px] font-bold text-gray-500 uppercase tracking-widest w-28">Status</th>
                      <th className="px-5 py-3 text-left text-[10px] font-bold text-gray-500 uppercase tracking-widest">Creator</th>
                      <th className="px-5 py-3 text-left text-[10px] font-bold text-gray-500 uppercase tracking-widest w-40">Date</th>
                      <th className="px-5 py-3 text-right text-[10px] font-bold text-gray-500 uppercase tracking-widest w-40">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-50">
                    {versions.map((ver) => (
                      <tr
                        key={ver.version}
                        className={`hover:bg-blue-50/30 transition-colors ${ver.status === "ACTIVE" ? "bg-blue-50/20" : ""}`}
                      >
                        <td className="px-5 py-4">
                          <span className={`text-sm font-bold font-mono ${ver.status === "ACTIVE" ? "text-blue-600 underline decoration-2 underline-offset-4" : "text-gray-900"}`}>
                            v{ver.version}
                          </span>
                        </td>
                        <td className="px-5 py-4">
                          <Badge variant={getStatusBadgeVariant(ver.status)} className="px-2.5 py-0.5 rounded-full text-[10px]">
                            {ver.status}
                          </Badge>
                        </td>
                        <td className="px-5 py-4">
                          <div className="flex items-center gap-2">
                            <div className="w-6 h-6 rounded-full bg-gray-100 flex items-center justify-center text-[9px] font-bold text-gray-500">
                              {ver.created_by[0].toUpperCase()}
                            </div>
                            <span className="text-xs text-gray-600 truncate max-w-[120px]">{ver.created_by}</span>
                          </div>
                        </td>
                        <td className="px-5 py-4 text-xs text-gray-400 font-mono">
                          {new Date(ver.created_at).toLocaleDateString()}
                        </td>
                        <td className="px-5 py-4 text-right">
                          <div className="flex justify-end gap-1">
                            {ver.status !== "ACTIVE" && (
                              <Button
                                size="sm"
                                variant="ghost"
                                className="h-8 w-8 p-0 rounded-full hover:bg-green-100 hover:text-green-600"
                                onClick={() => handleActivate(ver.version)}
                                title="Activate this version"
                              >
                                {ver.status === 'DRAFT' ? <Play className="h-3.5 w-3.5 fill-current" /> : <RotateCcw className="h-3.5 w-3.5" />}
                              </Button>
                            )}
                            {ver.status !== "ACTIVE" && (
                              <Button
                                size="sm"
                                variant="ghost"
                                className="h-8 w-8 p-0 rounded-full hover:bg-red-100 hover:text-red-600"
                                onClick={() => handleDeleteVersion(ver.version)}
                                title="Delete version"
                              >
                                <Trash2 className="h-3.5 w-3.5" />
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

        {/* Footer - Fixed */}
        <div className="border-t border-gray-100 p-6 bg-gray-50/80 rounded-b-2xl flex-shrink-0 backdrop-blur-md">
          <div className="flex items-center justify-between gap-4">
            <div className="flex gap-2">
              <Button variant="danger" onClick={handleDeleteAllVersions} className="flex items-center gap-2 shadow-sm border-red-200">
                <Trash2 className="h-4 w-4" />
                <span className="hidden sm:inline">Delete Entire Policy</span>
                <span className="sm:hidden">Delete All</span>
              </Button>
              {policy.status === "ACTIVE" && (
                <Button variant="secondary" onClick={handleArchive} className="bg-white">
                  <Archive className="h-4 w-4 mr-2" />
                  Archive
                </Button>
              )}
            </div>

            <div className="flex gap-3">
              <Button variant="secondary" onClick={onClose} className="bg-white px-6">
                Close
              </Button>
              {policy.status === "DRAFT" ? (
                <Button onClick={() => handleActivate()} className="px-8 shadow-lg shadow-blue-500/20">
                  <Play className="h-4 w-4 mr-2 fill-current" />
                  Activate Now
                </Button>
              ) : (
                <Button onClick={() => onEdit(policy)} className="px-8 shadow-lg shadow-blue-500/20">
                  <Edit className="h-4 w-4 mr-2" />
                  Edit Policy
                </Button>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
