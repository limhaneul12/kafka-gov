import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/Card";
import Button from "../components/ui/Button";
import Badge from "../components/ui/Badge";
import Loading from "../components/ui/Loading";
import { topicsAPI, clustersAPI } from "../services/api";
import { Plus, RefreshCw, Trash2, Search } from "lucide-react";
import type { Topic, KafkaCluster } from "../types";

export default function Topics() {
  const [topics, setTopics] = useState<Topic[]>([]);
  const [clusters, setClusters] = useState<KafkaCluster[]>([]);
  const [selectedCluster, setSelectedCluster] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [envFilter, setEnvFilter] = useState("");

  useEffect(() => {
    loadClusters();
  }, []);

  useEffect(() => {
    if (selectedCluster) {
      loadTopics();
    }
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

  const loadTopics = async () => {
    if (!selectedCluster) return;

    try {
      setLoading(true);
      const response = await topicsAPI.list(selectedCluster);
      setTopics(response.data.topics || []);
    } catch (error) {
      console.error("Failed to load topics:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (topicName: string) => {
    if (!confirm(`Are you sure you want to delete topic "${topicName}"?`)) {
      return;
    }

    try {
      await topicsAPI.delete(selectedCluster, topicName);
      await loadTopics();
    } catch (error) {
      console.error("Failed to delete topic:", error);
      alert("Failed to delete topic");
    }
  };

  const filteredTopics = topics.filter((topic) => {
    const matchesSearch = topic.name
      .toLowerCase()
      .includes(searchQuery.toLowerCase());
    const matchesEnv = !envFilter || topic.environment === envFilter;
    return matchesSearch && matchesEnv;
  });

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

  if (loading && !topics.length) {
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
          <h1 className="text-3xl font-bold text-gray-900">Topics</h1>
          <p className="mt-2 text-gray-600">Kafka 토픽을 관리합니다</p>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={loadTopics}>
            <RefreshCw className="h-4 w-4" />
            Refresh
          </Button>
          <Button>
            <Plus className="h-4 w-4" />
            Create Topic
          </Button>
        </div>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="grid gap-4 md:grid-cols-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Cluster
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
                Search
              </label>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search topics..."
                  className="w-full rounded-lg border border-gray-300 pl-10 pr-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Environment
              </label>
              <select
                value={envFilter}
                onChange={(e) => setEnvFilter(e.target.value)}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                <option value="">All</option>
                <option value="dev">Development</option>
                <option value="stg">Staging</option>
                <option value="prod">Production</option>
              </select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Topics Table */}
      <Card>
        <CardHeader>
          <CardTitle>Topics ({filteredTopics.length})</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">
                    Name
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">
                    Owner
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">
                    Partitions
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">
                    Replication
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">
                    Environment
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {filteredTopics.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-4 py-8 text-center text-gray-500">
                      No topics found
                    </td>
                  </tr>
                ) : (
                  filteredTopics.map((topic) => (
                    <tr key={topic.name} className="hover:bg-gray-50">
                      <td className="px-4 py-3 text-sm font-medium text-gray-900">
                        {topic.name}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600">
                        {topic.owner || "-"}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600">
                        {topic.partition_count || "-"}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600">
                        {topic.replication_factor || "-"}
                      </td>
                      <td className="px-4 py-3">
                        <Badge variant={getEnvBadgeVariant(topic.environment)}>
                          {topic.environment.toUpperCase()}
                        </Badge>
                      </td>
                      <td className="px-4 py-3">
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => handleDelete(topic.name)}
                        >
                          <Trash2 className="h-4 w-4 text-red-600" />
                        </Button>
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
