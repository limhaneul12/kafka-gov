import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/Card";
import Button from "../components/ui/Button";
import Badge from "../components/ui/Badge";
import Loading from "../components/ui/Loading";
import { topicsAPI, auditAPI, clustersAPI } from "../services/api";
import { RefreshCw, Users, TrendingUp, Activity, ExternalLink } from "lucide-react";
import { getTagColor } from "../utils/colors";
import { formatRetention } from "../utils/format";
import type { Topic, KafkaCluster } from "../types";

interface AuditActivity {
  activity_type: string;
  action: string;
  target: string;
  message: string;
  actor: string;
  team: string | null;
  timestamp: string;
  metadata: Record<string, unknown> | null;
}

interface EnvDistribution {
  dev: number;
  stg: number;
  prod: number;
}

export default function TeamAnalytics() {
  const { t } = useTranslation();
  const [topics, setTopics] = useState<Topic[]>([]);
  const [activities, setActivities] = useState<AuditActivity[]>([]);
  const [clusters, setClusters] = useState<KafkaCluster[]>([]);
  const [selectedCluster, setSelectedCluster] = useState<string>("");
  const [selectedTeam, setSelectedTeam] = useState<string>("");
  const [loading, setLoading] = useState(true);

  // owner가 있는 토픽에서만 팀 목록 추출
  const topicsWithOwners = topics.filter(t => t.owners && t.owners.length > 0);
  const teams = Array.from(new Set(topicsWithOwners.flatMap(t => t.owners))).filter(Boolean).sort();
  
  useEffect(() => {
    loadClusters();
  }, []);

  useEffect(() => {
    if (selectedCluster) {
      loadData();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedCluster]);

  const loadClusters = async () => {
    try {
      const response = await clustersAPI.listKafka();
      setClusters(response.data);
      if (response.data.length > 0) {
        setSelectedCluster(response.data[0].cluster_id);
      }
    } catch (error) {
      console.error("Failed to load clusters:", error);
    }
  };

  const loadData = async () => {
    if (!selectedCluster) return;

    try {
      setLoading(true);
      const [topicsData, activitiesData] = await Promise.all([
        topicsAPI.list(selectedCluster),
        auditAPI.recent(100).catch(() => ({ data: [] })),
      ]);

      const topicsPayload = topicsData.data as {
        items?: Topic[];
        topics?: Topic[];
      };
      setTopics(topicsPayload.items ?? topicsPayload.topics ?? []);
      setActivities(activitiesData.data || []);
    } catch (error) {
      console.error("Failed to load team analytics data:", error);
    } finally {
      setLoading(false);
    }
  };

  // 필터링된 데이터
  const filteredTopics = selectedTeam
    ? topicsWithOwners.filter(t => t.owners.includes(selectedTeam))
    : topicsWithOwners;

  // 메트릭 계산
  const totalTopics = filteredTopics.length;
  
  const envDistribution: EnvDistribution = filteredTopics.reduce((acc, t) => {
    const env = t.environment.toLowerCase() as keyof EnvDistribution;
    if (env in acc) {
      acc[env] = (acc[env] || 0) + 1;
    }
    return acc;
  }, { dev: 0, stg: 0, prod: 0 });

  const avgPartitions = totalTopics > 0
    ? Math.round(
        filteredTopics.reduce((sum, t) => sum + (t.partition_count || 0), 0) / totalTopics
      )
    : 0;

  // 최근 7일 활동 필터링
  const sevenDaysAgo = new Date();
  sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);
  const recentActivities = activities.filter(a => {
    const activityDate = new Date(a.timestamp);
    const isRecent = activityDate >= sevenDaysAgo;
    const isTeamMatch = !selectedTeam || a.team === selectedTeam;
    return isRecent && isTeamMatch;
  });

  // 액션별 그룹화
  const actionCounts = recentActivities.reduce((acc, a) => {
    const action = a.action || "UNKNOWN";
    acc[action] = (acc[action] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  const getEnvBadgeVariant = (env: string) => {
    switch (env.toLowerCase()) {
      case "prod":
        return "danger";
      case "stg":
        return "warning";
      case "dev":
        return "info";
      default:
        return "default";
    }
  };

  if (loading && topics.length === 0) {
    return (
      <div className="flex h-96 items-center justify-center">
        <Loading size="lg" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">{t("teamAnalytics.title")}</h1>
          <p className="mt-2 text-gray-600">
            {t("teamAnalytics.description")}
          </p>
        </div>
        <Button variant="secondary" onClick={loadData} disabled={loading}>
          <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          {t("common.filter")}
        </Button>
      </div>

      {/* Filters */}
      <Card className="p-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              {t("teamAnalytics.cluster")}
            </label>
            <select
              value={selectedCluster}
              onChange={(e) => setSelectedCluster(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              {clusters.map((cluster) => (
                <option key={cluster.cluster_id} value={cluster.cluster_id}>
                  {cluster.name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              <Users className="inline h-4 w-4 mr-1" />
              {t("teamAnalytics.team")}
            </label>
            <select
              value={selectedTeam}
              onChange={(e) => setSelectedTeam(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              <option value="">{t("teamAnalytics.allTeams")}</option>
              {teams.map((team) => (
                <option key={team} value={team}>
                  {team}
                </option>
              ))}
            </select>
          </div>
        </div>
      </Card>

      {/* Metric Cards */}
      <div className="grid gap-6 md:grid-cols-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">{t("teamAnalytics.totalTopics")}</p>
                <p className="text-3xl font-bold text-gray-900 mt-2">{totalTopics}</p>
                <p className="text-sm text-gray-500 mt-1">
                  {selectedTeam || t("teamAnalytics.allTeams")}
                </p>
              </div>
              <div className="h-12 w-12 rounded-full bg-blue-100 flex items-center justify-center">
                <TrendingUp className="h-6 w-6 text-blue-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">{t("teamAnalytics.envDistribution")}</p>
                <p className="text-3xl font-bold text-gray-900 mt-2">
                  {Object.keys(envDistribution).filter(k => envDistribution[k as keyof EnvDistribution] > 0).length}
                </p>
                <p className="text-sm text-gray-500 mt-1">
                  {Object.entries(envDistribution)
                    .filter(([, count]) => count > 0)
                    .map(([env, count]) => `${env.toUpperCase()}: ${count}`)
                    .join(" / ") || "-"}
                </p>
              </div>
              <div className="h-12 w-12 rounded-full bg-green-100 flex items-center justify-center">
                <Activity className="h-6 w-6 text-green-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">{t("teamAnalytics.avgPartitions")}</p>
                <p className="text-3xl font-bold text-gray-900 mt-2">{avgPartitions}</p>
                <p className="text-sm text-gray-500 mt-1">
                  {totalTopics} {t("teamAnalytics.topicAvg")}
                </p>
              </div>
              <div className="h-12 w-12 rounded-full bg-purple-100 flex items-center justify-center">
                <TrendingUp className="h-6 w-6 text-purple-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">{t("teamAnalytics.last7Days")}</p>
                <p className="text-3xl font-bold text-gray-900 mt-2">
                  {recentActivities.length}
                </p>
                <p className="text-sm text-gray-500 mt-1">{t("teamAnalytics.recentActivities")}</p>
              </div>
              <div className="h-12 w-12 rounded-full bg-orange-100 flex items-center justify-center">
                <Activity className="h-6 w-6 text-orange-600" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Charts */}
      <div className="grid gap-6 md:grid-cols-2">
        {/* Environment Distribution Chart */}
        <Card>
          <CardHeader>
            <CardTitle>{t("teamAnalytics.topicDistributionByEnv")}</CardTitle>
            <p className="text-sm text-gray-600">{t("teamAnalytics.envSubtitle")}</p>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {(["prod", "stg", "dev"] as const).map((env) => {
                const count = envDistribution[env] || 0;
                const maxCount = Math.max(...Object.values(envDistribution), 1);
                const width = Math.max((count / maxCount) * 100, 5);
                
                return (
                  <div key={env} className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium text-gray-700 uppercase">
                        {env}
                      </span>
                      <span className="text-sm text-gray-600">{count}개</span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-8 relative overflow-hidden">
                      <div
                        className={`h-8 rounded-full flex items-center justify-center text-white text-sm font-medium transition-all ${
                          env === "prod"
                            ? "bg-red-500"
                            : env === "stg"
                            ? "bg-yellow-500"
                            : "bg-blue-500"
                        }`}
                        style={{ width: `${width}%` }}
                      >
                        {width > 20 && count > 0 && `${count}개`}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>

        {/* Activity Trend Chart */}
        <Card>
          <CardHeader>
            <CardTitle>{t("teamAnalytics.activityTrend")}</CardTitle>
            <p className="text-sm text-gray-600">{t("teamAnalytics.activitySubtitle")}</p>
          </CardHeader>
          <CardContent>
            {Object.keys(actionCounts).length === 0 ? (
              <div className="text-center py-12 text-gray-500">
                {t("teamAnalytics.noActivities")}
              </div>
            ) : (
              <div className="space-y-4">
                {Object.entries(actionCounts).map(([action, count]) => {
                  const maxCount = Math.max(...Object.values(actionCounts), 1);
                  const width = Math.max((count / maxCount) * 100, 5);
                  
                  return (
                    <div key={action} className="space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium text-gray-700">
                          {action}
                        </span>
                        <span className="text-sm text-gray-600">{count}건</span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-8 relative overflow-hidden">
                        <div
                          className="h-8 bg-blue-500 rounded-full flex items-center justify-center text-white text-sm font-medium transition-all"
                          style={{ width: `${width}%` }}
                        >
                          {width > 30 && `${count}건`}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Topics Table */}
      <Card>
        <CardHeader>
          <CardTitle>{t("teamAnalytics.topics")}</CardTitle>
          <p className="text-sm text-gray-600">
            {selectedTeam ? `${selectedTeam} ${t("teamAnalytics.topicsSubtitle")}` : t("teamAnalytics.allTopicsSubtitle")}
          </p>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">
                    {t("teamAnalytics.topic")}
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">
                    {t("teamAnalytics.environment")}
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">
                    {t("teamAnalytics.partitions")}
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">
                    {t("teamAnalytics.replication")}
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">
                    {t("teamAnalytics.retention")}
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">
                    {t("teamAnalytics.tags")}
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">
                    {t("teamAnalytics.slo")}
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">
                    {t("teamAnalytics.sla")}
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">
                    {t("teamAnalytics.doc")}
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {filteredTopics.length === 0 ? (
                  <tr>
                    <td colSpan={9} className="px-4 py-8 text-center text-gray-500">
                      {selectedTeam ? t("teamAnalytics.noTopicsForTeam") : t("teamAnalytics.noTopics")}
                    </td>
                  </tr>
                ) : (
                  filteredTopics.map((topic) => (
                    <tr key={topic.name} className="hover:bg-gray-50">
                      <td className="px-4 py-3 text-sm font-medium text-gray-900">
                        {topic.name}
                      </td>
                      <td className="px-4 py-3">
                        <Badge variant={getEnvBadgeVariant(topic.environment)}>
                          {topic.environment.toUpperCase()}
                        </Badge>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600">
                        {topic.partition_count || "-"}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600">
                        {topic.replication_factor || "-"}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600">
                        {formatRetention(topic.retention_ms)}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex flex-wrap gap-1">
                          {topic.tags && topic.tags.length > 0 ? (
                            topic.tags.map((tag) => (
                              <span
                                key={tag}
                                className={`inline-flex items-center px-2 py-1 rounded-md text-xs font-medium ${getTagColor(tag)}`}
                              >
                                {tag}
                              </span>
                            ))
                          ) : (
                            <span className="text-sm text-gray-400">-</span>
                          )}
                        </div>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600">
                        {topic.slo || "-"}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600">
                        {topic.sla || "-"}
                      </td>
                      <td className="px-4 py-3 text-sm">
                        {topic.doc ? (
                          <a
                            href={topic.doc}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-blue-600 hover:text-blue-800 flex items-center gap-1"
                          >
                            <ExternalLink className="h-3 w-3" />
                            Link
                          </a>
                        ) : (
                          <span className="text-gray-400">-</span>
                        )}
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
