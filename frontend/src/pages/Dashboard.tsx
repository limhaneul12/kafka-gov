import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/Card";
import Button from "../components/ui/Button";
import Loading from "../components/ui/Loading";
import { analysisAPI, testConnection } from "../services/api";
import { Activity, Database, FileCode, List, Wifi } from "lucide-react";
import type { Statistics } from "../types";

export default function Dashboard() {
  const [stats, setStats] = useState<Statistics | null>(null);
  const [loading, setLoading] = useState(true);
  const [connectionStatus, setConnectionStatus] = useState<string>("");

  useEffect(() => {
    loadStatistics();
    checkConnection();
  }, []);

  const checkConnection = async () => {
    const result = await testConnection();
    if (result.success) {
      setConnectionStatus("✅ 백엔드 연결 성공");
    } else {
      setConnectionStatus(`❌ 백엔드 연결 실패: ${JSON.stringify(result.details)}`);
      console.error("Connection details:", result);
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
        <Button onClick={checkConnection} variant="secondary">
          <Wifi className="h-4 w-4" />
          연결 테스트
        </Button>
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

      {/* 통계 카드 */}
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Total Topics</p>
                <p className="mt-2 text-3xl font-bold text-gray-900">
                  {stats?.topic_count || 0}
                </p>
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
