import { useEffect, useMemo, useState } from "react";
import { useParams, useSearchParams, Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { topicsAPI, metricsAPI } from "../services/api";
import { ArrowLeft, AlertCircle, CheckCircle, Info, HardDrive, Database, RefreshCw, Loader2 } from "lucide-react";
import { toast } from "sonner";
import Button from "../components/ui/Button";

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

interface PartitionDetail {
  partition: number;
  size: number;
  leader: number;
  replicas: number[];
  isr: number[];
  offset_lag: number;
}

interface StorageMetrics {
  total_size: number;
  max_partition_size: number;
  min_partition_size: number;
  avg_partition_size: number;
}

interface TopicMetrics {
  topic_name: string;
  partition_count: number;
  storage: StorageMetrics;
  partitions: PartitionDetail[];
}

export default function TopicDetail() {
  const { t } = useTranslation();
  const { topicName } = useParams<{ topicName: string }>();
  const [searchParams] = useSearchParams();
  const clusterId = searchParams.get("cluster_id");

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<TopicDetailData | null>(null);
  const [activeTab, setActiveTab] = useState<"topic" | "consumer">("topic");
  const [metricsData, setMetricsData] = useState<TopicMetrics | null>(null);
  const [metricsLoading, setMetricsLoading] = useState(false);
  const [syncLoading, setSyncLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

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

  // Fetch metrics data separately
  useEffect(() => {
    if (!topicName || !clusterId || activeTab !== "topic") return;

    const fetchMetrics = async () => {
      setMetricsLoading(true);

      try {
        const liveResponse = await metricsAPI.getTopicMetricsLive(clusterId, topicName);
        console.log("✅ Topic live metrics received:", liveResponse.data);
        setMetricsData(liveResponse.data);
      } catch (liveError) {
        console.error("⚠️ Failed to fetch live metrics, fallback to snapshot:", liveError);

        try {
          const snapshotResponse = await metricsAPI.getTopicMetrics(clusterId, topicName);
          console.log("✅ Topic snapshot metrics received:", snapshotResponse.data);
          setMetricsData(snapshotResponse.data);
        } catch (snapshotError) {
          console.error("❌ Failed to fetch snapshot metrics:", snapshotError);
          toast.error(t("topic.detail.metricsLoadFailed"), {
            description: snapshotError instanceof Error ? snapshotError.message : undefined,
          });
        }
      } finally {
        setMetricsLoading(false);
      }
    };

    fetchMetrics();
  }, [topicName, clusterId, activeTab, t]);

  const hasMetrics = useMemo(() => {
    if (!metricsData) {
      return false;
    }

    const partitionCount = metricsData.partition_count ?? metricsData.partitions?.length ?? 0;
    const storage = metricsData.storage;
    const hasStorageMetrics =
      !!storage &&
      [storage.total_size, storage.max_partition_size, storage.min_partition_size, storage.avg_partition_size]
        .some((value) => value > 0);

    return partitionCount > 0 || hasStorageMetrics;
  }, [metricsData]);

  const loadMetricsAfterAction = async () => {
    if (!topicName || !clusterId) return;

    try {
      setMetricsLoading(true);
      const response = await metricsAPI.getTopicMetricsLive(clusterId, topicName);
      setMetricsData(response.data);
    } catch (err) {
      console.error("Failed to reload metrics:", err);
    } finally {
      setMetricsLoading(false);
    }
  };

  const handleRefreshSnapshot = async () => {
    if (!clusterId || !topicName) return;

    try {
      setRefreshing(true);
      toast.info(t("topic.detail.metricsRefreshStarted"));
      const response = await metricsAPI.getTopicMetricsLive(clusterId, topicName);
      toast.success(t("topic.detail.metricsRefreshTriggered"));
      setMetricsData(response.data);
    } catch (error) {
      console.error("Failed to trigger refresh:", error);
      toast.error(t("topic.detail.metricsRefreshFailed"), {
        description: error instanceof Error ? error.message : undefined,
      });
    } finally {
      setRefreshing(false);
    }
  };

  const handleSyncMetrics = async () => {
    if (!clusterId) return;

    try {
      setSyncLoading(true);
      toast.info(t("topic.detail.metricsSyncStarted"));
      await metricsAPI.syncMetrics(clusterId);
      toast.success(t("topic.detail.metricsSyncTriggered"));
      await loadMetricsAfterAction();
    } catch (error) {
      console.error("Failed to sync metrics:", error);
      toast.error(t("topic.detail.metricsSyncFailed"), {
        description: error instanceof Error ? error.message : undefined,
      });
    } finally {
      setSyncLoading(false);
    }
  };

  const formatRetention = (ms: number): string => {
    const days = Math.floor(ms / (1000 * 60 * 60 * 24));
    const hours = Math.floor((ms % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
    if (days > 0) return `${days}d ${hours}h`;
    return `${hours}h`;
  };

  const formatBytes = (bytes: number): string => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${(bytes / Math.pow(k, i)).toFixed(2)} ${sizes[i]}`;
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

  const renderMetricsContent = () => {
    if (metricsLoading) {
      return (
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-center py-8">
            <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
            <span className="ml-3 text-gray-600">Loading metrics...</span>
          </div>
        </div>
      );
    }

    if (hasMetrics && metricsData) {
      const metrics = metricsData;

      return (
        <>
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center gap-2 mb-4">
              <HardDrive className="w-5 h-5 text-gray-600" />
              <h2 className="text-lg font-semibold">저장용량 메트릭</h2>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-blue-50 p-4 rounded-lg">
                <p className="text-sm text-gray-600">전체 크기</p>
                <p className="text-xl font-bold text-blue-600">
                  {formatBytes(metrics.storage.total_size)}
                </p>
              </div>
              <div className="bg-green-50 p-4 rounded-lg">
                <p className="text-sm text-gray-600">평균 파티션 크기</p>
                <p className="text-xl font-bold text-green-600">
                  {formatBytes(metrics.storage.avg_partition_size)}
                </p>
              </div>
              <div className="bg-orange-50 p-4 rounded-lg">
                <p className="text-sm text-gray-600">최대 파티션 크기</p>
                <p className="text-xl font-bold text-orange-600">
                  {formatBytes(metrics.storage.max_partition_size)}
                </p>
              </div>
              <div className="bg-purple-50 p-4 rounded-lg">
                <p className="text-sm text-gray-600">최소 파티션 크기</p>
                <p className="text-xl font-bold text-purple-600">
                  {formatBytes(metrics.storage.min_partition_size)}
                </p>
              </div>
            </div>
          </div>

          {/* Partition Details */}
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center gap-2 mb-4">
              <Database className="w-5 h-5 text-gray-600" />
              <h2 className="text-lg font-semibold">파티션 상세 정보</h2>
            </div>
            {metrics.partitions.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-2 text-left text-sm font-medium text-gray-600">Partition</th>
                      <th className="px-4 py-2 text-left text-sm font-medium text-gray-600">Size</th>
                      <th className="px-4 py-2 text-left text-sm font-medium text-gray-600">Leader</th>
                      <th className="px-4 py-2 text-left text-sm font-medium text-gray-600">Replicas</th>
                      <th className="px-4 py-2 text-left text-sm font-medium text-gray-600">ISR</th>
                      <th className="px-4 py-2 text-left text-sm font-medium text-gray-600">Offset Lag</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200">
                    {metrics.partitions.map((partition) => (
                      <tr key={partition.partition} className="hover:bg-gray-50">
                        <td className="px-4 py-3 text-sm font-medium">{partition.partition}</td>
                        <td className="px-4 py-3 text-sm">{formatBytes(partition.size)}</td>
                        <td className="px-4 py-3 text-sm">
                          <span className="px-2 py-1 bg-blue-100 text-blue-700 rounded text-xs font-medium">
                            Broker {partition.leader}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-sm">
                          <div className="flex gap-1">
                            {partition.replicas.map((replica) => (
                              <span key={replica} className="px-2 py-1 bg-gray-100 text-gray-700 rounded text-xs">
                                {replica}
                              </span>
                            ))}
                          </div>
                        </td>
                        <td className="px-4 py-3 text-sm">
                          <div className="flex gap-1">
                            {partition.isr.map((isr) => (
                              <span key={isr} className="px-2 py-1 bg-green-100 text-green-700 rounded text-xs">
                                {isr}
                              </span>
                            ))}
                          </div>
                        </td>
                        <td className="px-4 py-3 text-sm">
                          <span className={`font-medium ${partition.offset_lag > 0 ? 'text-red-600' : 'text-green-600'}`}>
                            {partition.offset_lag.toLocaleString()}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="rounded-lg border border-dashed border-gray-200 bg-gray-50 p-6 text-center text-sm text-gray-600">
                저장된 스냅샷에는 파티션 상세 정보가 포함되지 않았습니다.
              </div>
            )}
          </div>
        </>
      );
    }

    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="text-center space-y-2">
          <p className="text-gray-600">{t('topic.detail.noMetricsTitle')}</p>
          <p className="text-sm text-gray-500">{t('topic.detail.noMetricsDescription')}</p>
          <div className="flex justify-center gap-2">
            <Button
              variant="secondary"
              size="sm"
              onClick={handleRefreshSnapshot}
              disabled={refreshing || syncLoading}
            >
              <RefreshCw className="w-4 h-4" />
              {t('topic.detail.refreshMetrics')}
            </Button>
            <Button
              variant="primary"
              size="sm"
              onClick={handleSyncMetrics}
              disabled={syncLoading || refreshing}
            >
              <RefreshCw className="w-4 h-4" />
              {t('topic.detail.syncMetrics')}
            </Button>
          </div>
        </div>
      </div>
    );
  };

  const renderMetricsToolbar = () => {
    if (!clusterId) return null;

    return (
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold">📦 {t('topic.detail.overview')}</h2>
          <p className="text-sm text-gray-500">{t('topic.detail.metricsHint')}</p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="secondary"
            size="sm"
            onClick={handleRefreshSnapshot}
            disabled={refreshing || syncLoading}
          >
            {refreshing ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                {t('topic.detail.refreshing')}
              </>
            ) : (
              <>
                <RefreshCw className="w-4 h-4" />
                {t('topic.detail.refreshMetrics')}
              </>
            )}
          </Button>
          <Button
            variant="primary"
            size="sm"
            onClick={handleSyncMetrics}
            disabled={syncLoading || refreshing}
          >
            {syncLoading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                {t('topic.detail.syncing')}
              </>
            ) : (
              <>
                <RefreshCw className="w-4 h-4" />
                {t('topic.detail.syncMetrics')}
              </>
            )}
          </Button>
        </div>
      </div>
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-600">{t('topic.detail.loading')}</p>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-6">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-600">❌ {error || t('topic.detail.error')}</p>
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

      {/* Tab Navigation */}
      <div className="bg-white rounded-lg shadow">
        <div className="border-b border-gray-200">
          <div className="flex">
            <button
              onClick={() => setActiveTab("topic")}
              className={`flex-1 px-6 py-4 text-center font-medium transition-colors ${
                activeTab === "topic"
                  ? "text-blue-600 border-b-2 border-blue-600 bg-blue-50"
                  : "text-gray-600 hover:text-gray-900 hover:bg-gray-50"
              }`}
            >
              📦 Topic
            </button>
            <button
              onClick={() => setActiveTab("consumer")}
              className={`flex-1 px-6 py-4 text-center font-medium transition-colors ${
                activeTab === "consumer"
                  ? "text-blue-600 border-b-2 border-blue-600 bg-blue-50"
                  : "text-gray-600 hover:text-gray-900 hover:bg-gray-50"
              }`}
            >
              👥 Consumer Group
            </button>
          </div>
        </div>
      </div>

      {/* Topic Tab Content */}
      {activeTab === "topic" && (
        <div className="space-y-6">
          {/* Topic Info Card */}
          <div className="bg-white rounded-lg shadow p-6">
            {renderMetricsToolbar()}
            <div className="mt-4 grid grid-cols-1 sm:grid-cols-3 gap-6">
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

          {/* Storage Metrics Card */}
          {renderMetricsContent()}
        </div>
      )}

      {/* Consumer Group Tab Content */}
      {activeTab === "consumer" && (
        <div className="space-y-6">
          {/* Consumer Insight Card */}
          <div className="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-lg shadow p-6 border border-blue-200">
            <h2 className="text-lg font-semibold mb-4">📊 {t('topic.detail.governanceInsights')}</h2>
            
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
              <h2 className="text-lg font-semibold mb-4">🚨 {t('topic.detail.governanceAlerts')}</h2>
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
            <h2 className="text-lg font-semibold mb-4">👥 {t('topic.detail.consumerGroupsHealth')}</h2>
            
            {data.consumer_groups.length === 0 ? (
              <p className="text-gray-500 text-center py-8">{t('topic.detail.noConsumerGroups')}</p>
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
      )}
    </div>
  );
}
