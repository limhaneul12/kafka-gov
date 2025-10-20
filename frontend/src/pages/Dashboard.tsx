import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/Card";
import Button from "../components/ui/Button";
import Loading from "../components/ui/Loading";
import { analysisAPI, testAPIConnection, topicsAPI, clustersAPI } from "../services/api";
import { Activity, Database, FileCode, List, Wifi, RefreshCw } from "lucide-react";
import type { Statistics, KafkaCluster } from "../types";

export default function Dashboard() {
  const [stats, setStats] = useState<Statistics | null>(null);
  const [clusters, setClusters] = useState<KafkaCluster[]>([]);
  const [selectedCluster, setSelectedCluster] = useState<string>("");
  const [topicCount, setTopicCount] = useState<number>(0);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<string>("");

  useEffect(() => {
    loadClusters();
    loadStatistics();
    checkConnection();
  }, []);

  useEffect(() => {
    if (selectedCluster) {
      loadTopicCount();
    }
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
      toast.error('클러스터 로드 실패', {
        description: '클러스터 목록을 불러오지 못했습니다.'
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

  const checkConnection = async () => {
    const result = await testAPIConnection();
    if (result.success) {
      setConnectionStatus("✅ 백엔드 연결 성공");
      toast.success('연결 성공', {
        description: '백엔드 서버에 정상적으로 연결되었습니다.'
      });
    } else {
      setConnectionStatus(`❌ 백엔드 연결 실패: ${JSON.stringify(result.details)}`);
      console.error("Connection details:", result);
      toast.error('연결 실패', {
        description: '백엔드 서버 연결에 실패했습니다.'
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
      await Promise.all([loadStatistics(), loadTopicCount()]);
      toast.success('동기화 완료', {
        description: '통계 데이터가 업데이트되었습니다.'
      });
    } catch (error) {
      console.error('Sync failed:', error);
      toast.error('동기화 실패', {
        description: '데이터를 새로고침하는데 실패했습니다.'
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
          <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
          <p className="mt-2 text-gray-600">
            Kafka 클러스터 상태를 한눈에 확인하세요
          </p>
        </div>
        <div className="flex gap-2">
          <Button onClick={handleSync} variant="secondary" disabled={syncing}>
            <RefreshCw className={`h-4 w-4 ${syncing ? "animate-spin" : ""}`} />
            {syncing ? "동기화 중..." : "동기화"}
          </Button>
          <Button onClick={checkConnection} variant="secondary">
            <Wifi className="h-4 w-4" />
            연결 테스트
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
                Kafka 클러스터:
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
                <p className="text-sm font-medium text-gray-600">Total Topics</p>
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
                  Registered Schemas
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
                <p className="text-sm font-medium text-gray-600">Correlations</p>
                <p className="mt-2 text-3xl font-bold text-gray-900">
                  {stats?.correlation_count || 0}
                </p>
              </div>
              <div className="rounded-full bg-purple-100 p-3">
                <Activity className="h-6 w-6 text-purple-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Health Status</p>
                <p className="mt-2 text-3xl font-bold text-green-600">Healthy</p>
              </div>
              <div className="rounded-full bg-green-100 p-3">
                <Database className="h-6 w-6 text-green-600" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

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
