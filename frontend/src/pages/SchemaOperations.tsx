import { useCallback, useEffect, useMemo, useState } from "react";
import { CheckCircle2, ClipboardList, History, ShieldAlert, XCircle } from "lucide-react";
import { toast } from "sonner";

import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/Card";
import Badge from "../components/ui/Badge";
import Button from "../components/ui/Button";
import Loading from "../components/ui/Loading";
import schemaApi from "../services/schemaApi";
import type { ApprovalRequestResponse, AuditActivityResponse } from "../types/schema";
import { extractErrorMessage } from "../utils/error";
import { promptApprovalDecision } from "../utils/schemaGovernancePrompts";

const formatDateTime = (value: string | null) => {
  if (!value) return "N/A";
  return new Date(value).toLocaleString();
};

export default function SchemaOperations() {
  const [approvals, setApprovals] = useState<ApprovalRequestResponse[]>([]);
  const [activities, setActivities] = useState<AuditActivityResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [approvalSearch, setApprovalSearch] = useState("");
  const [approvalStatusFilter, setApprovalStatusFilter] = useState("all");
  const [auditSearch, setAuditSearch] = useState("");
  const [auditTypeFilter, setAuditTypeFilter] = useState("all");
  const [auditActionFilter, setAuditActionFilter] = useState("all");
  const [approvalPage, setApprovalPage] = useState(1);
  const [auditPage, setAuditPage] = useState(1);
  const [pendingDecisionId, setPendingDecisionId] = useState<string | null>(null);
  const pageSize = 5;

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const [approvalData, activityData] = await Promise.all([
        schemaApi.listApprovalRequests({ resource_type: "schema", limit: 200 }),
        schemaApi.getAuditHistory({ limit: 200 }),
      ]);
      setApprovals(approvalData);
      setActivities(activityData);
    } catch (error) {
      toast.error(extractErrorMessage(error, "Failed to load approval and audit data"));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    setApprovalPage(1);
  }, [approvalSearch, approvalStatusFilter]);

  useEffect(() => {
    setAuditPage(1);
  }, [auditSearch, auditTypeFilter, auditActionFilter]);

  const filteredApprovals = useMemo(() => {
    const query = approvalSearch.trim().toLowerCase();
    return approvals.filter((request) => {
      const matchesStatus =
        approvalStatusFilter === "all" || request.status.toLowerCase() === approvalStatusFilter;
      const matchesQuery =
        !query ||
        [
          request.resource_name,
          request.summary,
          request.justification,
          request.requested_by,
          request.change_type,
        ]
          .filter(Boolean)
          .some((value) => value.toLowerCase().includes(query));
      return matchesStatus && matchesQuery;
    });
  }, [approvalSearch, approvalStatusFilter, approvals]);

  const filteredActivities = useMemo(() => {
    const query = auditSearch.trim().toLowerCase();
    return activities.filter((activity) => {
      const matchesType =
        auditTypeFilter === "all" || activity.activity_type.toLowerCase() === auditTypeFilter;
      const matchesAction =
        auditActionFilter === "all" || activity.action.toLowerCase() === auditActionFilter;
      const matchesQuery =
        !query ||
        [activity.target, activity.message, activity.actor, activity.action, activity.activity_type]
          .filter(Boolean)
          .some((value) => value.toLowerCase().includes(query));
      return matchesType && matchesAction && matchesQuery;
    });
  }, [activities, auditActionFilter, auditSearch, auditTypeFilter]);

  const approvalPageCount = Math.max(1, Math.ceil(filteredApprovals.length / pageSize));
  const auditPageCount = Math.max(1, Math.ceil(filteredActivities.length / pageSize));

  const pagedApprovals = useMemo(
    () => filteredApprovals.slice((approvalPage - 1) * pageSize, approvalPage * pageSize),
    [approvalPage, filteredApprovals],
  );
  const pagedActivities = useMemo(
    () => filteredActivities.slice((auditPage - 1) * pageSize, auditPage * pageSize),
    [auditPage, filteredActivities],
  );

  const decide = async (requestId: string, action: "approve" | "reject") => {
    const decision = promptApprovalDecision(action);
    if (!decision) return;

    try {
      setPendingDecisionId(requestId);
      if (action === "approve") {
        await schemaApi.approveApprovalRequest(requestId, {
          approver: decision.approver,
          decision_reason: decision.decisionReason,
        });
        toast.success("Approval request approved");
      } else {
        await schemaApi.rejectApprovalRequest(requestId, {
          approver: decision.approver,
          decision_reason: decision.decisionReason,
        });
        toast.success("Approval request rejected");
      }
      await load();
    } catch (error) {
      toast.error(extractErrorMessage(error, `Failed to ${action} approval request`));
    } finally {
      setPendingDecisionId(null);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loading size="lg" />
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-[1200px] mx-auto">
      <div className="flex items-end justify-between">
        <div>
          <div className="flex items-center gap-2 text-indigo-600 font-semibold text-sm mb-1">
            <ShieldAlert className="h-4 w-4" />
            Governance Workflow
          </div>
          <h1 className="text-3xl font-bold text-gray-900 tracking-tight">Approvals & Audit</h1>
          <p className="mt-1 text-sm text-gray-500">
            Review pending schema approvals and inspect recent governance activity.
          </p>
        </div>
        <Button onClick={() => void load()} variant="secondary">
          Refresh
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="text-sm font-medium text-gray-500">Pending Approvals</div>
            <div className="text-3xl font-bold mt-1 text-amber-600">
              {filteredApprovals.filter((request) => request.status === "pending").length}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-sm font-medium text-gray-500">Recent Activities</div>
            <div className="text-3xl font-bold mt-1 text-blue-600">{filteredActivities.length}</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-sm font-medium text-gray-500">Schema Events</div>
            <div className="text-3xl font-bold mt-1 text-emerald-600">
              {filteredActivities.filter((item) => item.activity_type === "schema").length}
            </div>
          </CardContent>
        </Card>
      </div>

      <Card className="overflow-hidden border-gray-200 shadow-sm">
        <CardHeader className="bg-white border-b border-gray-100">
          <CardTitle className="text-lg font-bold flex items-center gap-2">
            <ClipboardList className="h-5 w-5" />
            Pending Approval Requests
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <div className="p-4 border-b border-gray-100 bg-gray-50 grid grid-cols-1 md:grid-cols-3 gap-3">
            <input
              value={approvalSearch}
              onChange={(event) => setApprovalSearch(event.target.value)}
              placeholder="Search subject, summary, requester..."
              className="rounded-lg border border-gray-200 px-3 py-2 text-sm"
            />
            <select
              value={approvalStatusFilter}
              onChange={(event) => setApprovalStatusFilter(event.target.value)}
              className="rounded-lg border border-gray-200 px-3 py-2 text-sm bg-white"
            >
              <option value="all">All statuses</option>
              <option value="pending">Pending</option>
              <option value="approved">Approved</option>
              <option value="rejected">Rejected</option>
            </select>
            <div className="text-xs text-gray-500 flex items-center md:justify-end">
              Showing {pagedApprovals.length} of {filteredApprovals.length} approval requests
            </div>
          </div>
          {filteredApprovals.length === 0 ? (
            <div className="p-6 text-sm text-gray-500">No pending schema approval requests.</div>
          ) : (
            <div className="divide-y divide-gray-100">
              {pagedApprovals.map((request) => (
                <div key={request.request_id} className="p-5 flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-semibold text-gray-900">{request.resource_name}</span>
                      <Badge variant={approvalStatusVariant(request.status)} className="uppercase">
                        {request.status}
                      </Badge>
                    </div>
                    <p className="text-sm text-gray-600">{request.summary}</p>
                    <p className="text-xs text-gray-500">{request.justification}</p>
                    <div className="text-xs text-gray-400">
                      Requested by {request.requested_by} · {formatDateTime(request.requested_at)}
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      variant="secondary"
                      onClick={() => void decide(request.request_id, "approve")}
                      disabled={pendingDecisionId === request.request_id}
                    >
                      <CheckCircle2 className="h-4 w-4" />
                      Approve
                    </Button>
                    <Button
                      variant="danger"
                      onClick={() => void decide(request.request_id, "reject")}
                      disabled={pendingDecisionId === request.request_id}
                    >
                      <XCircle className="h-4 w-4" />
                      Reject
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
          <PaginationControls
            currentPage={approvalPage}
            totalPages={approvalPageCount}
            onChange={setApprovalPage}
          />
        </CardContent>
      </Card>

      <Card className="overflow-hidden border-gray-200 shadow-sm">
        <CardHeader className="bg-white border-b border-gray-100">
          <CardTitle className="text-lg font-bold flex items-center gap-2">
            <History className="h-5 w-5" />
            Recent Audit Activity
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <div className="p-4 border-b border-gray-100 bg-gray-50 grid grid-cols-1 md:grid-cols-4 gap-3">
            <input
              value={auditSearch}
              onChange={(event) => setAuditSearch(event.target.value)}
              placeholder="Search target, message, actor..."
              className="rounded-lg border border-gray-200 px-3 py-2 text-sm md:col-span-2"
            />
            <select
              value={auditTypeFilter}
              onChange={(event) => setAuditTypeFilter(event.target.value)}
              className="rounded-lg border border-gray-200 px-3 py-2 text-sm bg-white"
            >
              <option value="all">All activity types</option>
              <option value="approval">Approval</option>
              <option value="schema">Schema</option>
              <option value="registry">Registry</option>
            </select>
            <select
              value={auditActionFilter}
              onChange={(event) => setAuditActionFilter(event.target.value)}
              className="rounded-lg border border-gray-200 px-3 py-2 text-sm bg-white"
            >
              <option value="all">All actions</option>
              <option value="requested">Requested</option>
              <option value="approved">Approved</option>
              <option value="rejected">Rejected</option>
              <option value="sync">Sync</option>
            </select>
          </div>
          {filteredActivities.length === 0 ? (
            <div className="p-6 text-sm text-gray-500">No recent governance activity.</div>
          ) : (
            <div className="divide-y divide-gray-100">
              {pagedActivities.map((activity, index) => (
                <div key={`${activity.activity_type}-${activity.action}-${activity.timestamp}-${index}`} className="p-5">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-sm font-semibold text-gray-900">{activity.target}</span>
                    <Badge variant={activityTypeVariant(activity.activity_type)} className="uppercase">
                      {activity.activity_type}
                    </Badge>
                    <Badge variant={activityActionVariant(activity.action)} className="uppercase">
                      {activity.action}
                    </Badge>
                  </div>
                  <p className="text-sm text-gray-600">{activity.message}</p>
                  <div className="text-xs text-gray-400 mt-1">
                    {activity.actor} · {formatDateTime(activity.timestamp)}
                  </div>
                </div>
              ))}
            </div>
          )}
          <PaginationControls
            currentPage={auditPage}
            totalPages={auditPageCount}
            onChange={setAuditPage}
          />
        </CardContent>
      </Card>
    </div>
  );
}

function PaginationControls({
  currentPage,
  totalPages,
  onChange,
}: {
  currentPage: number;
  totalPages: number;
  onChange: (page: number) => void;
}) {
  if (totalPages <= 1) {
    return null;
  }

  return (
    <div className="px-4 py-3 border-t border-gray-100 bg-white flex items-center justify-between">
      <div className="text-xs text-gray-500">
        Page {currentPage} of {totalPages}
      </div>
      <div className="flex items-center gap-2">
        <Button
          variant="secondary"
          onClick={() => onChange(Math.max(1, currentPage - 1))}
          disabled={currentPage === 1}
        >
          Previous
        </Button>
        <Button
          variant="secondary"
          onClick={() => onChange(Math.min(totalPages, currentPage + 1))}
          disabled={currentPage === totalPages}
        >
          Next
        </Button>
      </div>
    </div>
  );
}

function approvalStatusVariant(status: string) {
  switch (status.toLowerCase()) {
    case "approved":
      return "success" as const;
    case "rejected":
      return "danger" as const;
    default:
      return "warning" as const;
  }
}

function activityTypeVariant(activityType: string) {
  switch (activityType.toLowerCase()) {
    case "approval":
      return "warning" as const;
    case "schema":
      return "info" as const;
    default:
      return "secondary" as const;
  }
}

function activityActionVariant(action: string) {
  switch (action.toLowerCase()) {
    case "approved":
      return "success" as const;
    case "rejected":
      return "danger" as const;
    case "sync":
      return "secondary" as const;
    default:
      return "info" as const;
  }
}
