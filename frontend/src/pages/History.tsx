import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/Card";
import Button from "../components/ui/Button";
import Badge from "../components/ui/Badge";
import Loading from "../components/ui/Loading";
import { auditAPI } from "../services/api";
import { RefreshCw, Clock, User, FileText } from "lucide-react";

interface AuditLog {
  activity_type: string;
  action: string;
  target: string;
  message: string;
  actor: string;
  team: string | null;
  timestamp: string;
  metadata: Record<string, unknown> | null;
}

export default function History() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [limit, setLimit] = useState(50);

  useEffect(() => {
    loadHistory();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [limit]);

  const loadHistory = async () => {
    try {
      setLoading(true);
      const response = await auditAPI.recent(limit);
      setLogs(response.data || []);
    } catch (error) {
      console.error("Failed to load history:", error);
    } finally {
      setLoading(false);
    }
  };

  const getActivityTypeColor = (type: string) => {
    switch (type?.toLowerCase()) {
      case "topic":
        return "info";
      case "schema":
        return "success";
      case "policy":
        return "warning";
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
                  {logs.filter((l) => l.action?.includes("CREATE") || l.action?.includes("UPDATE")).length}
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
                  {logs.filter((l) => l.action?.includes("DELETE") || l.action?.includes("FAILED")).length}
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
                  {new Set(logs.map((l) => l.actor)).size}
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
          <CardTitle>Recent Activities</CardTitle>
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
                    Status
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">
                    Details
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {logs.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-4 py-8 text-center text-gray-500">
                      활동 내역이 없습니다
                    </td>
                  </tr>
                ) : (
                  logs.map((log, idx) => (
                    <tr key={`${log.actor}-${log.timestamp}-${idx}`} className="hover:bg-gray-50">
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
                        <Badge variant="success">
                          SUCCESS
                        </Badge>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600">
                        {log.message || "-"}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
