import { Fragment, useCallback, useEffect, useMemo, useState } from "react";
import { ChevronDown, ChevronUp, Clock, FileText, RefreshCw, User } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/Card";
import Badge from "../components/ui/Badge";
import Button from "../components/ui/Button";
import Loading from "../components/ui/Loading";
import { auditAPI } from "../services/api";
import type { AuditLog } from "../types";

interface ApprovalMetadata {
  required: boolean;
  summary: string | null;
  overridePresent: boolean;
  approver: string | null;
  reason: string | null;
}

interface RiskMetadata {
  level: string | null;
  reasons: string[];
}

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null;

const readApprovalMetadata = (metadata: Record<string, unknown> | null): ApprovalMetadata => {
  if (!metadata) {
    return {
      required: false,
      summary: null,
      overridePresent: false,
      approver: null,
      reason: null,
    };
  }

  const approval = isRecord(metadata.approval) ? metadata.approval : null;
  const approvalOverride = isRecord(metadata.approval_override) ? metadata.approval_override : null;

  return {
    required: approval?.approval_required === true,
    summary: typeof approval?.summary === "string" ? approval.summary : null,
    overridePresent: approval?.approval_override_present === true || approvalOverride !== null,
    approver: typeof approvalOverride?.approver === "string" ? approvalOverride.approver : null,
    reason: typeof approvalOverride?.reason === "string" ? approvalOverride.reason : null,
  };
};

const readRiskMetadata = (metadata: Record<string, unknown> | null): RiskMetadata => {
  if (!metadata) {
    return { level: null, reasons: [] };
  }

  const risk = isRecord(metadata.risk) ? metadata.risk : null;
  const reasons = Array.isArray(risk?.reasons)
    ? risk.reasons.filter((reason): reason is string => typeof reason === "string")
    : [];

  return {
    level: typeof risk?.risk_level === "string" ? risk.risk_level : null,
    reasons,
  };
};

const getApprovalBadgeVariant = (approval: ApprovalMetadata): "default" | "success" | "warning" | "info" => {
  if (approval.overridePresent) {
    return "success";
  }
  if (approval.required) {
    return "warning";
  }
  if (approval.summary) {
    return "info";
  }
  return "default";
};

const getApprovalBadgeLabel = (approval: ApprovalMetadata): string => {
  if (approval.overridePresent) {
    return "OVERRIDDEN";
  }
  if (approval.required) {
    return "REQUIRED";
  }
  if (approval.summary) {
    return "CHECKED";
  }
  return "N/A";
};

const getRiskBadgeVariant = (level: string | null): "default" | "danger" | "warning" | "info" => {
  if (level === "critical") {
    return "danger";
  }
  if (level === "high") {
    return "warning";
  }
  if (level === "medium" || level === "low") {
    return "info";
  }
  return "default";
};

export default function History() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [limit, setLimit] = useState(50);
  const [activityFilter, setActivityFilter] = useState("all");
  const [approvalFilter, setApprovalFilter] = useState("all");
  const [riskFilter, setRiskFilter] = useState("all");
  const [expandedLogKey, setExpandedLogKey] = useState<string | null>(null);

  const loadHistory = useCallback(async () => {
    try {
      setLoading(true);
      const response = await auditAPI.recent(limit);
      setLogs(response.data || []);
    } catch (error) {
      console.error("Failed to load history:", error);
    } finally {
      setLoading(false);
    }
  }, [limit]);

  useEffect(() => {
    void loadHistory();
  }, [loadHistory]);

  const getActivityTypeColor = (type: string) => {
    switch (type?.toLowerCase()) {
      case "schema":
        return "success";
      case "approval":
        return "info";
      default:
        return "default";
    }
  };

  const getActionColor = (action: string) => {
    if (action.includes("CREATE") || action.includes("ADD")) return "text-green-600";
    if (action.includes("DELETE") || action.includes("REMOVE")) return "text-red-600";
    if (action.includes("UPDATE") || action.includes("MODIFY")) return "text-blue-600";
    return "text-gray-600";
  };

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleString("ko-KR", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  };

  const filteredLogs = useMemo(() => {
    return logs.filter((log) => {
      const approval = readApprovalMetadata(log.metadata);
      const risk = readRiskMetadata(log.metadata);

      const matchesActivity =
        activityFilter === "all" || log.activity_type.toLowerCase() === activityFilter;

      const matchesApproval =
        approvalFilter === "all" ||
        (approvalFilter === "overridden" && approval.overridePresent) ||
        (approvalFilter === "required" && approval.required && !approval.overridePresent) ||
        (approvalFilter === "checked" && !approval.required && !!approval.summary) ||
        (approvalFilter === "none" && !approval.required && !approval.overridePresent && !approval.summary);

      const matchesRisk = riskFilter === "all" || risk.level === riskFilter;

      return matchesActivity && matchesApproval && matchesRisk;
    });
  }, [activityFilter, approvalFilter, logs, riskFilter]);

  const toggleExpanded = (key: string) => {
    setExpandedLogKey((current) => (current === key ? null : key));
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
          <h1 className="text-3xl font-bold text-gray-900">Activity History</h1>
          <p className="mt-2 text-gray-600">
            시스템 활동 내역 및 변경 이력을 확인합니다
          </p>
        </div>
        <div className="flex gap-2">
          <select
            value={limit}
            onChange={(e) => setLimit(Number(e.target.value))}
            className="rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            <option value={20}>최근 20개</option>
            <option value={50}>최근 50개</option>
            <option value={100}>최근 100개</option>
            <option value={200}>최근 200개</option>
          </select>
          <Button variant="secondary" onClick={loadHistory}>
            <RefreshCw className="h-4 w-4" />
            Refresh
          </Button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid gap-6 md:grid-cols-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Total Events</p>
                <p className="mt-2 text-3xl font-bold text-gray-900">{logs.length}</p>
              </div>
              <div className="rounded-full bg-blue-100 p-3">
                <FileText className="h-6 w-6 text-blue-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Success</p>
                <p className="mt-2 text-3xl font-bold text-green-600">
                  {filteredLogs.filter((l) => l.action?.includes("CREATE") || l.action?.includes("UPDATE")).length}
                </p>
              </div>
              <div className="rounded-full bg-green-100 p-3">
                <Clock className="h-6 w-6 text-green-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Failed</p>
                <p className="mt-2 text-3xl font-bold text-red-600">
                  {filteredLogs.filter((l) => l.action?.includes("DELETE") || l.action?.includes("FAILED")).length}
                </p>
              </div>
              <div className="rounded-full bg-red-100 p-3">
                <Clock className="h-6 w-6 text-red-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Unique Users</p>
                <p className="mt-2 text-3xl font-bold text-purple-600">
                  {new Set(filteredLogs.map((l) => l.actor)).size}
                </p>
              </div>
              <div className="rounded-full bg-purple-100 p-3">
                <User className="h-6 w-6 text-purple-600" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Activity Timeline */}
      <Card>
        <CardHeader>
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <CardTitle>Recent Activities</CardTitle>
            <div className="grid gap-2 sm:grid-cols-3">
              <select
                value={activityFilter}
                onChange={(e) => setActivityFilter(e.target.value)}
                className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                <option value="all">All Resources</option>
                <option value="schema">Schema</option>
                <option value="approval">Approval</option>
              </select>
              <select
                value={approvalFilter}
                onChange={(e) => setApprovalFilter(e.target.value)}
                className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                <option value="all">All Approval States</option>
                <option value="required">Approval Required</option>
                <option value="overridden">Overridden</option>
                <option value="checked">Checked Only</option>
                <option value="none">No Approval Data</option>
              </select>
              <select
                value={riskFilter}
                onChange={(e) => setRiskFilter(e.target.value)}
                className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                <option value="all">All Risk Levels</option>
                <option value="critical">Critical</option>
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
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
                    Timestamp
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">
                    User
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">
                    Action
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">
                    Resource
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">
                    Approval
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">
                    Details
                  </th>
                  <th className="px-4 py-3 text-right text-sm font-medium text-gray-600">
                    View
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {filteredLogs.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="px-4 py-8 text-center text-gray-500">
                      활동 내역이 없습니다
                    </td>
                  </tr>
                ) : (
                  filteredLogs.map((log, idx) => {
                    const approval = readApprovalMetadata(log.metadata);
                    const risk = readRiskMetadata(log.metadata);
                    const rowKey = `${log.actor}-${log.timestamp}-${idx}`;
                    const isExpanded = expandedLogKey === rowKey;

                    return (
                      <Fragment key={rowKey}>
                        <tr key={rowKey} className="hover:bg-gray-50 align-top">
                          <td className="px-4 py-3 text-sm text-gray-600">
                            {formatTimestamp(log.timestamp)}
                          </td>
                          <td className="px-4 py-3">
                            <div className="flex items-center gap-2">
                              <User className="h-4 w-4 text-gray-400" />
                              <div>
                                <span className="text-sm font-medium text-gray-900">
                                  {log.actor}
                                </span>
                                {log.team && (
                                  <p className="text-xs text-gray-500">{log.team}</p>
                                )}
                              </div>
                            </div>
                          </td>
                          <td className="px-4 py-3">
                            <span className={`text-sm font-medium ${getActionColor(log.action)}`}>
                              {log.action}
                            </span>
                          </td>
                          <td className="px-4 py-3">
                            <div>
                              <Badge variant={getActivityTypeColor(log.activity_type)}>
                                {log.activity_type}
                              </Badge>
                              <p className="mt-1 text-sm text-gray-600">{log.target}</p>
                            </div>
                          </td>
                          <td className="px-4 py-3">
                            <div className="space-y-2">
                              <Badge variant={getApprovalBadgeVariant(approval)}>
                                {getApprovalBadgeLabel(approval)}
                              </Badge>
                              {approval.approver && (
                                <p className="text-xs text-gray-500">by {approval.approver}</p>
                              )}
                              {risk.level && (
                                <Badge variant={getRiskBadgeVariant(risk.level)}>
                                  {risk.level.toUpperCase()}
                                </Badge>
                              )}
                            </div>
                          </td>
                          <td className="px-4 py-3 text-sm text-gray-600">
                            <div className="space-y-1">
                              <p>{log.message || "-"}</p>
                              {approval.summary && (
                                <p className="text-xs text-gray-500">{approval.summary}</p>
                              )}
                              {approval.reason && (
                                <p className="text-xs text-gray-500">Reason: {approval.reason}</p>
                              )}
                              {risk.reasons.length > 0 && (
                                <p className="text-xs text-gray-500">
                                  Risk: {risk.reasons.join(", ")}
                                </p>
                              )}
                            </div>
                          </td>
                          <td className="px-4 py-3 text-right">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => toggleExpanded(rowKey)}
                            >
                              {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                            </Button>
                          </td>
                        </tr>
                        {isExpanded && (
                          <tr className="bg-slate-50">
                            <td colSpan={7} className="px-4 py-4">
                              <div className="grid gap-4 md:grid-cols-3">
                                <div className="space-y-2">
                                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Approval</p>
                                  <p className="text-sm text-slate-700">State: {getApprovalBadgeLabel(approval)}</p>
                                  <p className="text-sm text-slate-700">Summary: {approval.summary ?? "-"}</p>
                                  <p className="text-sm text-slate-700">Approver: {approval.approver ?? "-"}</p>
                                  <p className="text-sm text-slate-700">Reason: {approval.reason ?? "-"}</p>
                                </div>
                                <div className="space-y-2">
                                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Risk</p>
                                  <p className="text-sm text-slate-700">Level: {risk.level ?? "-"}</p>
                                  <p className="text-sm text-slate-700">
                                    Reasons: {risk.reasons.length > 0 ? risk.reasons.join(", ") : "-"}
                                  </p>
                                </div>
                                <div className="space-y-2">
                                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Raw Metadata</p>
                                  <pre className="max-h-48 overflow-auto rounded-lg bg-slate-900 p-3 text-xs text-slate-100">
                                    {JSON.stringify(log.metadata, null, 2)}
                                  </pre>
                                </div>
                              </div>
                            </td>
                          </tr>
                        )}
                      </Fragment>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
