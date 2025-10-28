import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/Card";
import Button from "../components/ui/Button";
import Loading from "../components/ui/Loading";
import Badge from "../components/ui/Badge";
import { analysisAPI, testAPIConnection, topicsAPI, clustersAPI, consumerAPI } from "../services/api";
import { FileCode, List, Wifi, RefreshCw, Users, TrendingUp } from "lucide-react";
import type { Statistics, KafkaCluster, ConsumerGroup } from "../types";

export default function Dashboard() {
  const { t } = useTranslation();
  const [stats, setStats] = useState<Statistics | null>(null);
  const [clusters, setClusters] = useState<KafkaCluster[]>([]);
  const [selectedCluster, setSelectedCluster] = useState<string>("");
  const [topicCount, setTopicCount] = useState<number>(0);
  const [consumerGroups, setConsumerGroups] = useState<ConsumerGroup[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<string>("");

  useEffect(() => {
    loadClusters();
    loadStatistics();
    checkConnection();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (selectedCluster) {
      loadTopicCount();
      loadConsumerGroups();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedCluster]);

  const loadClusters = async () => {
    try {
      const response = await clustersAPI.listKafka();
      const clusterList = response.data;
      setClusters(clusterList);
      if (clusterList.length > 0) {
        setSelectedCluster(clusterList[0].cluster_id);
      }
    } catch (error) {
      console.error("Failed to load clusters:", error);
      toast.error(t('error.general'), {
        description: t('error.network')
      });
    }
  };

  const loadTopicCount = async () => {
    if (!selectedCluster) return;
    try {
      const response = await topicsAPI.list(selectedCluster);
      setTopicCount(response.data.topics?.length || 0);
    } catch (error) {
      console.error("Failed to load topic count:", error);
      setTopicCount(0);
    }
  };

  const loadConsumerGroups = async () => {
    if (!selectedCluster) return;
    try {
      const response = await consumerAPI.listGroups(selectedCluster);
      setConsumerGroups(response.data.groups || []);
    } catch (error) {
      console.error("Failed to load consumer groups:", error);
      setConsumerGroups([]);
    }
  };

  const checkConnection = async () => {
    const result = await testAPIConnection();
    if (result.success) {
      setConnectionStatus(`✅ ${t('dashboard.healthy')}`);
      toast.success(t('common.success'), {
        description: t('connection.test')
      });
    } else {
      setConnectionStatus(`❌ ${t('dashboard.unhealthy')}: ${JSON.stringify(result.details)}`);
      console.error("Connection details:", result);
      toast.error(t('common.error'), {
        description: t('error.network')
      });
    }
  };

  const loadStatistics = async () => {
    try {
      setLoading(true);
      const response = await analysisAPI.statistics();
      setStats(response.data);
    } catch (error) {
      console.error("Failed to load statistics:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleSync = async () => {
    try {
      setSyncing(true);
      await Promise.all([loadStatistics(), loadTopicCount(), loadConsumerGroups()]);
      toast.success(t('common.success'), {
        description: t('dashboard.subtitle')
      });
    } catch (error) {
      console.error('Sync failed:', error);
      toast.error(t('common.error'), {
        description: t('error.network')
      });
    } finally {
      setSyncing(false);
    }
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
          <h1 className="text-3xl font-bold text-gray-900">{t('dashboard.title')}</h1>
          <p className="mt-2 text-gray-600">
            {t('dashboard.subtitle')}
          </p>
        </div>
        <div className="flex gap-2">
          <Button onClick={handleSync} variant="secondary" disabled={syncing}>
            <RefreshCw className={`h-4 w-4 ${syncing ? "animate-spin" : ""}`} />
            {syncing ? t('common.loading') : t('common.filter')}
          </Button>
          <Button onClick={checkConnection} variant="secondary">
            <Wifi className="h-4 w-4" />
            {t('connection.test')}
          </Button>
        </div>
      </div>

      {/* 연결 상태 */}
      {connectionStatus && (
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-2">
              <Wifi className={connectionStatus.startsWith("✅") ? "text-green-600" : "text-red-600"} />
              <p className="text-sm font-mono">{connectionStatus}</p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* 클러스터 선택 */}
      {clusters.length > 0 && (
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <label className="text-sm font-medium text-gray-700">
                {t('dashboard.selectCluster')}:
              </label>
              <select
                value={selectedCluster}
                onChange={(e) => setSelectedCluster(e.target.value)}
                className="rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                {clusters.map((cluster) => (
                  <option key={cluster.cluster_id} value={cluster.cluster_id}>
                    {cluster.name} ({cluster.cluster_id})
                  </option>
                ))}
              </select>
            </div>
          </CardContent>
        </Card>
      )}

      {/* 통계 카드 */}
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">{t('dashboard.totalTopics')}</p>
                <p className="mt-2 text-3xl font-bold text-gray-900">
                  {selectedCluster ? topicCount : (stats?.topic_count || 0)}
                </p>
                {selectedCluster && (
                  <p className="text-xs text-gray-500 mt-1">
                    선택된 클러스터
                  </p>
                )}
              </div>
              <div className="rounded-full bg-blue-100 p-3">
                <List className="h-6 w-6 text-blue-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">
                  {t('dashboard.registeredSchemas')}
                </p>
                <p className="mt-2 text-3xl font-bold text-gray-900">
                  {stats?.schema_count || 0}
                </p>
              </div>
              <div className="rounded-full bg-green-100 p-3">
                <FileCode className="h-6 w-6 text-green-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">{t('dashboard.consumerGroups')}</p>
                <p className="mt-2 text-3xl font-bold text-gray-900">
                  {consumerGroups.length}
                </p>
                {selectedCluster && consumerGroups.length > 0 && (
                  <p className="text-xs text-gray-500 mt-1">
                    {consumerGroups.filter(g => g.state === 'Stable').length} stable
                  </p>
                )}
              </div>
              <div className="rounded-full bg-purple-100 p-3">
                <Users className="h-6 w-6 text-purple-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">{t('dashboard.totalLag')}</p>
                <p className="mt-2 text-3xl font-bold text-gray-900">
                  {consumerGroups.reduce((sum, g) => sum + g.lag_stats.total_lag, 0).toLocaleString()}
                </p>
                {consumerGroups.length > 0 && (
                  <p className="text-xs text-gray-500 mt-1">
                    Across all groups
                  </p>
                )}
              </div>
              <div className="rounded-full bg-orange-100 p-3">
                <TrendingUp className="h-6 w-6 text-orange-600" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Consumer Groups 상태 */}
      {selectedCluster && consumerGroups.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Consumer Groups Status</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 md:grid-cols-3">
              <div className="flex items-center justify-between p-4 bg-emerald-50 rounded-lg">
                <div>
                  <p className="text-sm font-medium text-emerald-900">{t('dashboard.stable')}</p>
                  <p className="text-2xl font-bold text-emerald-700">
                    {consumerGroups.filter(g => g.state === 'Stable').length}
                  </p>
                </div>
                <Badge color="emerald">Healthy</Badge>
              </div>
              <div className="flex items-center justify-between p-4 bg-yellow-50 rounded-lg">
                <div>
                  <p className="text-sm font-medium text-yellow-900">{t('dashboard.rebalancing')}</p>
                  <p className="text-2xl font-bold text-yellow-700">
                    {consumerGroups.filter(g => g.state === 'Rebalancing').length}
                  </p>
                </div>
                <Badge color="yellow">Active</Badge>
              </div>
              <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                <div>
                  <p className="text-sm font-medium text-gray-900">{t('dashboard.other')}</p>
                  <p className="text-2xl font-bold text-gray-700">
                    {consumerGroups.filter(g => g.state !== 'Stable' && g.state !== 'Rebalancing').length}
                  </p>
                </div>
                <Badge color="gray">Idle</Badge>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* 최근 활동 */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Activities</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-gray-600">
            최근 활동 내역이 여기에 표시됩니다.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
