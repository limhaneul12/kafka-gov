import { useEffect, useState, useCallback } from "react";
import { useParams, useSearchParams, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/Card";
import Button from "../components/ui/Button";
import Badge from "../components/ui/Badge";
import Loading from "../components/ui/Loading";
import { consumerAPI } from "../services/api";
import { ArrowLeft, RefreshCw, Copy } from "lucide-react";
import type { ConsumerGroupSummary, ConsumerGroupMetrics } from "../types";
import OperationsTab from "../components/consumer/OperationsTab";
import GovernanceTab from "../components/consumer/GovernanceTab";
import MembersTab from "../components/consumer/MembersTab";
import PartitionsTab from "../components/consumer/PartitionsTab";
import LiveMonitoring from "../components/consumer/LiveMonitoring";
import LagHistoryChart from "../components/consumer/LagHistoryChart";
import type { LiveSnapshot } from "../hooks/useConsumerWebSocket";

type TabType = "operations" | "governance" | "members" | "partitions";

interface LagDataPoint {
  timestamp: string;
  totalLag: number;
  p95Lag: number;
}

export default function ConsumerDetail() {
  const { groupId } = useParams<{ groupId: string }>();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const clusterId = searchParams.get("cluster_id") || undefined;

  const [activeTab, setActiveTab] = useState<TabType>("operations");
  const [summary, setSummary] = useState<ConsumerGroupSummary | null>(null);
  const [metrics, setMetrics] = useState<ConsumerGroupMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [isLiveMode, setIsLiveMode] = useState(true);
  const [lagHistory, setLagHistory] = useState<LagDataPoint[]>([]);

  useEffect(() => {
    if (groupId && clusterId) {
      loadData();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [groupId, clusterId]);

  const loadData = async () => {
    if (!groupId || !clusterId) return;

    try {
      setLoading(true);
      const [summaryRes, metricsRes] = await Promise.all([
        consumerAPI.getSummary(clusterId, groupId),
        consumerAPI.getMetrics(clusterId, groupId),
      ]);
      setSummary(summaryRes.data);
      setMetrics(metricsRes.data);
    } catch (error) {
      console.error("Failed to load consumer group details:", error);
      toast.error("Failed to load consumer group details");
    } finally {
      setLoading(false);
    }
  };

  const getStateColor = (state: string) => {
    switch (state.toLowerCase()) {
      case "stable":
        return "emerald";
      case "rebalancing":
        return "yellow";
      case "empty":
        return "gray";
      case "dead":
        return "rose";
      default:
        return "blue";
    }
  };

  const getFairnessColor = (gini: number) => {
    if (gini < 0.2) return "emerald";
    if (gini < 0.4) return "yellow";
    return "rose";
  };

  const getFairnessLevel = (gini: number) => {
    if (gini < 0.2) return "Balanced";
    if (gini < 0.4) return "Slight Skew";
    return "Hotspot";
  };

  const handleCopyGroupId = () => {
    if (groupId) {
      navigator.clipboard.writeText(groupId);
      toast.success("Group ID copied to clipboard");
    }
  };

  // WebSocket 실시간 업데이트 핸들러
  const handleLiveUpdate = useCallback((snapshot: LiveSnapshot) => {
    if (!isLiveMode) return;

    // Summary 업데이트
    setSummary((prev) => ({
      ...prev!,
      state: snapshot.state,
      lag: {
        p50: snapshot.lag_stats.p50_lag,
        p95: snapshot.lag_stats.p95_lag,
        max: snapshot.lag_stats.max_lag,
        total: snapshot.lag_stats.total_lag,
      },
      fairness_gini: snapshot.fairness_gini,
      stuck: snapshot.partitions
        .filter((p) => p.lag && p.lag > 10000)
        .map((p) => ({
          topic: p.topic,
          partition: p.partition,
          lag: p.lag!,
        })),
    }));

    // Lag 히스토리 업데이트 (최근 30개만 유지)
    setLagHistory((prev) => {
      const newDataPoint: LagDataPoint = {
        timestamp: snapshot.timestamp,
        totalLag: snapshot.lag_stats.total_lag,
        p95Lag: snapshot.lag_stats.p95_lag,
      };
      const updated = [...prev, newDataPoint];
      return updated.slice(-30); // 최근 30개 (5분간 = 30 * 10초)
    });
  }, [isLiveMode]);

  const tabs: { id: TabType; label: string }[] = [
    { id: "operations", label: "Operations" },
    { id: "governance", label: "Governance" },
    { id: "members", label: "Members" },
    { id: "partitions", label: "Partitions" },
  ];

  // cluster_id 검증
  if (!clusterId || clusterId.trim() === "") {
    return (
      <div className="flex h-96 items-center justify-center">
        <div className="text-center">
          <p className="text-xl text-gray-700 font-semibold">Missing cluster_id</p>
          <p className="text-gray-500 mt-2">
            Please provide cluster_id in URL query parameter
          </p>
          <Button
            className="mt-4"
            variant="primary"
            onClick={() => navigate("/consumers")}
          >
            Back to Consumers
          </Button>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex h-96 items-center justify-center">
        <Loading size="lg" />
      </div>
    );
  }

  if (!summary || !metrics) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500">Consumer group not found</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Live Monitoring Banner */}
      {isLiveMode && groupId && clusterId && (
        <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-4">
          <LiveMonitoring
            clusterId={clusterId}
            groupId={groupId}
            onSnapshotUpdate={handleLiveUpdate}
          />
        </div>
      )}

      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button
            variant="secondary"
            onClick={() => navigate("/consumers")}
          >
            <ArrowLeft className="h-4 w-4" />
            Back
          </Button>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-3xl font-bold text-gray-900">{groupId}</h1>
              <Badge color={getStateColor(summary.state)}>{summary.state}</Badge>
            </div>
            <p className="mt-2 text-gray-600">Consumer Group Details</p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button
            variant={isLiveMode ? "primary" : "secondary"}
            onClick={() => setIsLiveMode(!isLiveMode)}
          >
            {isLiveMode ? "Live Mode On" : "Live Mode Off"}
          </Button>
          <Button variant="secondary" onClick={handleCopyGroupId}>
            <Copy className="h-4 w-4" />
            Copy ID
          </Button>
          <Button
            variant="secondary"
            onClick={loadData}
            disabled={isLiveMode}
          >
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        </div>
      </div>

      {/* Key Metrics Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium text-gray-600">
              Total Lag
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-gray-900">
              {summary.lag.total.toLocaleString()}
            </div>
            <p className="text-xs text-gray-500 mt-1">
              P95: {summary.lag.p95.toLocaleString()}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium text-gray-600">
              Rebalance Score
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-gray-900">
              {summary.rebalance_score.toFixed(1)}
            </div>
            <p className="text-xs text-gray-500 mt-1">
              {metrics.rebalance_score
                ? `${metrics.rebalance_score.rebalances_per_hour.toFixed(2)}/hr`
                : "No data"}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium text-gray-600">
              Fairness (Gini)
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-baseline gap-2">
              <div className="text-2xl font-bold text-gray-900">
                {summary.fairness_gini.toFixed(3)}
              </div>
              <Badge color={getFairnessColor(summary.fairness_gini)}>
                {getFairnessLevel(summary.fairness_gini)}
              </Badge>
            </div>
            <p className="text-xs text-gray-500 mt-1">
              {metrics.fairness.member_count} members
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium text-gray-600">
              Stuck Partitions
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-gray-900">
              {summary.stuck.length}
            </div>
            <p className="text-xs text-gray-500 mt-1">
              {summary.stuck.length > 0 ? "Requires attention" : "All healthy"}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Lag History Chart (Live Mode Only) */}
      {isLiveMode && lagHistory.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Total Lag History (Last 5 minutes)</CardTitle>
            <p className="text-sm text-gray-500 mt-1">
              Real-time lag tracking with 10-second intervals
            </p>
          </CardHeader>
          <CardContent>
            <LagHistoryChart data={lagHistory} />
            <div className="mt-4 flex gap-6 justify-center text-sm">
              <div className="flex items-center gap-2">
                <div className="w-8 h-0.5 bg-blue-500"></div>
                <span className="text-gray-600">Total Lag</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-8 h-0.5 bg-amber-500"></div>
                <span className="text-gray-600">P95 Lag</span>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Tabs */}
      <Card>
        <CardHeader>
          <div className="border-b border-gray-200">
            <nav className="-mb-px flex space-x-8">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`
                    whitespace-nowrap border-b-2 py-4 px-1 text-sm font-medium transition-colors
                    ${
                      activeTab === tab.id
                        ? "border-blue-500 text-blue-600"
                        : "border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700"
                    }
                  `}
                >
                  {tab.label}
                </button>
              ))}
            </nav>
          </div>
        </CardHeader>
        <CardContent className="pt-6">
          {activeTab === "operations" && (
            <OperationsTab
              summary={summary}
              metrics={metrics}
              groupId={groupId!}
              clusterId={clusterId!}
            />
          )}
          {activeTab === "governance" && (
            <GovernanceTab
              metrics={metrics}
              groupId={groupId!}
              clusterId={clusterId!}
            />
          )}
          {activeTab === "members" && (
            <MembersTab groupId={groupId!} clusterId={clusterId!} />
          )}
          {activeTab === "partitions" && (
            <PartitionsTab groupId={groupId!} clusterId={clusterId!} />
          )}
        </CardContent>
      </Card>
    </div>
  );
}
