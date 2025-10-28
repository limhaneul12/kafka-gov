import { useEffect, useState } from "react";
import { useParams, useSearchParams, Link } from "react-router-dom";
import { topicsAPI } from "../services/api";
import { ArrowLeft, AlertCircle, CheckCircle, Info } from "lucide-react";

interface ConsumerHealth {
  group_id: string;
  state: string;
  slo_compliance: number;
  lag_p50: number;
  lag_p95: number;
  lag_max: number;
  stuck_count: number;
  rebalance_score: number | null;
  fairness_gini: number;
  member_count: number;
  recommendation: string | null;
}

interface GovernanceAlert {
  severity: string;
  consumer_group: string;
  message: string;
  metric: string | null;
}

interface TopicConsumerInsight {
  total_consumers: number;
  healthy_consumers: number;
  unhealthy_consumers: number;
  avg_slo_compliance: number;
  avg_rebalance_score: number;
  total_stuck_partitions: number;
  partitions_with_consumers: number;
  total_partitions: number;
  summary: string;
}

interface TopicDetailData {
  topic: string;
  cluster_id: string;
  partitions: number;
  replication_factor: number;
  retention_ms: number;
  insight: TopicConsumerInsight;
  consumer_groups: ConsumerHealth[];
  governance_alerts: GovernanceAlert[];
}

export default function TopicDetail() {
  const { topicName } = useParams<{ topicName: string }>();
  const [searchParams] = useSearchParams();
  const clusterId = searchParams.get("cluster_id");

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<TopicDetailData | null>(null);

  useEffect(() => {
    console.log("🔍 TopicDetail useEffect triggered", { topicName, clusterId });
    
    if (!topicName || !clusterId) {
      console.error("❌ Missing parameters:", { topicName, clusterId });
      setError("Topic name or cluster ID is missing");
      setLoading(false);
      return;
    }

    const fetchTopicDetail = async () => {
      try {
        console.log("🚀 Fetching topic detail:", { clusterId, topicName });
        setLoading(true);
        setError(null);
        const response = await topicsAPI.getDetail(clusterId, topicName);
        console.log("✅ Topic detail received:", response.data);
        setData(response.data);
      } catch (err: unknown) {
        console.error("❌ Failed to fetch topic detail:", err);
        setError(err instanceof Error ? err.message : "Failed to load topic detail");
      } finally {
        setLoading(false);
      }
    };

    fetchTopicDetail();
  }, [topicName, clusterId]);

  const formatRetention = (ms: number): string => {
    const days = Math.floor(ms / (1000 * 60 * 60 * 24));
    const hours = Math.floor((ms % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
    if (days > 0) return `${days}d ${hours}h`;
    return `${hours}h`;
  };

  const getSeverityColor = (severity: string): string => {
    switch (severity) {
      case "error":
        return "text-red-600 bg-red-50 border-red-200";
      case "warning":
        return "text-yellow-600 bg-yellow-50 border-yellow-200";
      case "info":
        return "text-blue-600 bg-blue-50 border-blue-200";
      default:
        return "text-gray-600 bg-gray-50 border-gray-200";
    }
  };

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case "error":
        return <AlertCircle className="w-4 h-4" />;
      case "warning":
        return <AlertCircle className="w-4 h-4" />;
      case "info":
        return <Info className="w-4 h-4" />;
      default:
        return <Info className="w-4 h-4" />;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-600">Loading topic detail...</p>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-6">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-600">❌ {error || "Failed to load topic detail"}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link
            to={`/topics?cluster_id=${clusterId}`}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div>
            <h1 className="text-2xl font-bold">{data.topic}</h1>
            <p className="text-gray-500 text-sm">Cluster: {data.cluster_id}</p>
          </div>
        </div>
      </div>

      {/* Topic Info Card */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold mb-4">📦 Topic Information</h2>
        <div className="grid grid-cols-3 gap-6">
          <div>
            <p className="text-sm text-gray-500">Partitions</p>
            <p className="text-2xl font-bold">{data.partitions}</p>
          </div>
          <div>
            <p className="text-sm text-gray-500">Replication Factor</p>
            <p className="text-2xl font-bold">{data.replication_factor}</p>
          </div>
          <div>
            <p className="text-sm text-gray-500">Retention</p>
            <p className="text-2xl font-bold">{formatRetention(data.retention_ms)}</p>
          </div>
        </div>
      </div>

      {/* Consumer Insight Card */}
      <div className="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-lg shadow p-6 border border-blue-200">
        <h2 className="text-lg font-semibold mb-4">📊 Consumer Insight (거버넌스 지표)</h2>
        
        <div className="mb-4 p-4 bg-white rounded-lg border border-blue-100">
          <p className="text-base font-medium text-gray-800">{data.insight.summary}</p>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-white p-4 rounded-lg">
            <p className="text-sm text-gray-500">Total Consumers</p>
            <p className="text-2xl font-bold">{data.insight.total_consumers}</p>
          </div>
          <div className="bg-white p-4 rounded-lg">
            <p className="text-sm text-gray-500">Healthy</p>
            <p className="text-2xl font-bold text-green-600">{data.insight.healthy_consumers}</p>
          </div>
          <div className="bg-white p-4 rounded-lg">
            <p className="text-sm text-gray-500">Unhealthy</p>
            <p className="text-2xl font-bold text-red-600">{data.insight.unhealthy_consumers}</p>
          </div>
          <div className="bg-white p-4 rounded-lg">
            <p className="text-sm text-gray-500">Stuck Partitions</p>
            <p className="text-2xl font-bold text-orange-600">{data.insight.total_stuck_partitions}</p>
          </div>
          <div className="bg-white p-4 rounded-lg">
            <p className="text-sm text-gray-500">Avg SLO Compliance</p>
            <p className="text-2xl font-bold">{(data.insight.avg_slo_compliance * 100).toFixed(1)}%</p>
          </div>
          <div className="bg-white p-4 rounded-lg">
            <p className="text-sm text-gray-500">Avg Rebalance Score</p>
            <p className="text-2xl font-bold">
              {data.insight.avg_rebalance_score > 0 
                ? `${data.insight.avg_rebalance_score.toFixed(1)}/100` 
                : 'N/A'}
            </p>
          </div>
          <div className="bg-white p-4 rounded-lg">
            <p className="text-sm text-gray-500">Partitions Consumed</p>
            <p className="text-2xl font-bold">
              {data.insight.partitions_with_consumers}/{data.insight.total_partitions}
            </p>
          </div>
        </div>
      </div>

      {/* Governance Alerts */}
      {data.governance_alerts.length > 0 && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-4">🚨 Governance Alerts</h2>
          <div className="space-y-2">
            {data.governance_alerts.map((alert, idx) => (
              <div
                key={idx}
                className={`flex items-start gap-3 p-3 rounded-lg border ${getSeverityColor(alert.severity)}`}
              >
                {getSeverityIcon(alert.severity)}
                <div className="flex-1">
                  <p className="font-medium">{alert.consumer_group}</p>
                  <p className="text-sm">{alert.message}</p>
                </div>
                {alert.metric && (
                  <span className="text-xs px-2 py-1 bg-white rounded">{alert.metric}</span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Consumer Groups Health */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold mb-4">👥 Consumer Groups Health</h2>
        
        {data.consumer_groups.length === 0 ? (
          <p className="text-gray-500 text-center py-8">이 토픽을 소비하는 Consumer Group이 없습니다</p>
        ) : (
          <div className="space-y-4">
            {data.consumer_groups.map((consumer) => (
              <div
                key={consumer.group_id}
                className="border rounded-lg p-4 hover:shadow-md transition-shadow"
              >
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center gap-3">
                    {consumer.slo_compliance >= 0.95 && consumer.stuck_count === 0 ? (
                      <CheckCircle className="w-6 h-6 text-green-600" />
                    ) : (
                      <AlertCircle className="w-6 h-6 text-yellow-600" />
                    )}
                    <div>
                      <Link
                        to={`/consumers/${consumer.group_id}?cluster_id=${clusterId}`}
                        className="text-lg font-semibold hover:text-blue-600 hover:underline"
                      >
                        {consumer.group_id}
                      </Link>
                      <p className="text-sm text-gray-500">
                        State: <span className="font-medium">{consumer.state}</span> | Members: {consumer.member_count}
                      </p>
                    </div>
                  </div>
                  {consumer.recommendation && (
                    <span className="px-3 py-1 bg-yellow-100 text-yellow-800 text-sm rounded-full">
                      💡 {consumer.recommendation}
                    </span>
                  )}
                </div>

                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div>
                    <p className="text-xs text-gray-500">SLO Compliance</p>
                    <p className={`text-lg font-semibold ${consumer.slo_compliance >= 0.95 ? 'text-green-600' : 'text-red-600'}`}>
                      {(consumer.slo_compliance * 100).toFixed(1)}%
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500">P95 Lag</p>
                    <p className="text-lg font-semibold">{consumer.lag_p95.toLocaleString()}</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500">Max Lag</p>
                    <p className="text-lg font-semibold">{consumer.lag_max.toLocaleString()}</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500">Stuck</p>
                    <p className={`text-lg font-semibold ${consumer.stuck_count > 0 ? 'text-red-600' : 'text-green-600'}`}>
                      {consumer.stuck_count}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500">Rebalance Score</p>
                    <p className="text-lg font-semibold">
                      {consumer.rebalance_score !== null 
                        ? `${consumer.rebalance_score.toFixed(1)}/100` 
                        : 'N/A'}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500">Fairness (Gini)</p>
                    <p className="text-lg font-semibold">{consumer.fairness_gini.toFixed(2)}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
