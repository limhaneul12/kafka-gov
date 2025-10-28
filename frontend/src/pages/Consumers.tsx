import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Card, CardContent } from "../components/ui/Card";
import Button from "../components/ui/Button";
import Badge from "../components/ui/Badge";
import Loading from "../components/ui/Loading";
import { consumerAPI, clustersAPI } from "../services/api";
import { RefreshCw, Search, Users, TrendingUp, Activity } from "lucide-react";
import type { ConsumerGroup, KafkaCluster } from "../types";

export default function Consumers() {
  const navigate = useNavigate();
  const [groups, setGroups] = useState<ConsumerGroup[]>([]);
  const [clusters, setClusters] = useState<KafkaCluster[]>([]);
  const [selectedCluster, setSelectedCluster] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [stateFilter, setStateFilter] = useState<string[]>([]);
  const [lagThreshold, setLagThreshold] = useState<number | null>(null);

  useEffect(() => {
    loadClusters();
  }, []);

  useEffect(() => {
    if (selectedCluster) {
      loadGroups();
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
      toast.error("Failed to load clusters");
    }
  };

  const loadGroups = async () => {
    if (!selectedCluster) return;
    
    try {
      setLoading(true);
      const response = await consumerAPI.listGroups(selectedCluster);
      setGroups(response.data.groups || []);
    } catch (error) {
      console.error("Failed to load consumer groups:", error);
      toast.error("Failed to load consumer groups");
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

  const getLagLevel = (totalLag: number) => {
    if (totalLag === 0) return { label: "No Lag", color: "emerald" };
    if (totalLag < 1000) return { label: "Low", color: "blue" };
    if (totalLag < 5000) return { label: "Medium", color: "yellow" };
    return { label: "High", color: "rose" };
  };

  const filteredGroups = groups.filter((group) => {
    const matchesSearch =
      !searchQuery ||
      group.group_id.toLowerCase().includes(searchQuery.toLowerCase());

    const matchesState =
      stateFilter.length === 0 || stateFilter.includes(group.state);

    const matchesLag =
      lagThreshold === null || group.lag_stats.total_lag >= lagThreshold;

    return matchesSearch && matchesState && matchesLag;
  });

  const handleCardClick = (groupId: string) => {
    navigate(`/consumers/${groupId}?cluster_id=${selectedCluster}`);
  };

  if (loading && !groups.length) {
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
          <h1 className="text-3xl font-bold text-gray-900">Consumer Groups</h1>
          <p className="mt-2 text-gray-600">
            Monitor consumer group health, lag, and fairness
          </p>
        </div>
        <Button onClick={loadGroups} variant="secondary" disabled={loading}>
          <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </Button>
      </div>

      {/* Cluster Selection */}
      {clusters.length > 0 && (
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <label className="text-sm font-medium text-gray-700">
                Cluster:
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

      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="grid gap-4 md:grid-cols-3">
            {/* Search */}
            <div className="relative">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
              <input
                type="text"
                placeholder="Search consumer groups..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full rounded-lg border border-gray-300 py-2 pl-10 pr-4 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>

            {/* State Filter */}
            <div>
              <select
                value={stateFilter[0] || ""}
                onChange={(e) =>
                  setStateFilter(e.target.value ? [e.target.value] : [])
                }
                className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                <option value="">All States</option>
                <option value="Stable">Stable</option>
                <option value="Rebalancing">Rebalancing</option>
                <option value="Empty">Empty</option>
                <option value="Dead">Dead</option>
              </select>
            </div>

            {/* Lag Threshold */}
            <div>
              <select
                value={lagThreshold?.toString() || ""}
                onChange={(e) =>
                  setLagThreshold(e.target.value ? Number(e.target.value) : null)
                }
                className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                <option value="">All Lag Levels</option>
                <option value="1000">Lag &gt; 1,000</option>
                <option value="5000">Lag &gt; 5,000</option>
                <option value="10000">Lag &gt; 10,000</option>
              </select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Statistics */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Total Groups</p>
                <p className="mt-2 text-3xl font-bold text-gray-900">
                  {filteredGroups.length}
                </p>
              </div>
              <Users className="h-8 w-8 text-blue-500" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Stable</p>
                <p className="mt-2 text-3xl font-bold text-emerald-600">
                  {filteredGroups.filter((g) => g.state === "Stable").length}
                </p>
              </div>
              <Activity className="h-8 w-8 text-emerald-500" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Rebalancing</p>
                <p className="mt-2 text-3xl font-bold text-yellow-600">
                  {filteredGroups.filter((g) => g.state === "Rebalancing").length}
                </p>
              </div>
              <TrendingUp className="h-8 w-8 text-yellow-500" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Total Lag</p>
                <p className="mt-2 text-3xl font-bold text-gray-900">
                  {filteredGroups
                    .reduce((sum, g) => sum + g.lag_stats.total_lag, 0)
                    .toLocaleString()}
                </p>
              </div>
              <TrendingUp className="h-8 w-8 text-rose-500" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Consumer Groups Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {filteredGroups.map((group) => {
          const lagLevel = getLagLevel(group.lag_stats.total_lag);
          return (
            <Card
              key={group.group_id}
              className="cursor-pointer transition-all hover:shadow-lg"
              onClick={() => handleCardClick(group.group_id)}
            >
              <CardContent className="pt-6">
                <div className="space-y-4">
                  {/* Header */}
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <h3 className="font-semibold text-gray-900 truncate">
                        {group.group_id}
                      </h3>
                      <p className="text-sm text-gray-500 mt-1">
                        {group.member_count} member{group.member_count !== 1 ? "s" : ""} · {group.topic_count} topic{group.topic_count !== 1 ? "s" : ""}
                      </p>
                    </div>
                    <Badge color={getStateColor(group.state)}>{group.state}</Badge>
                  </div>

                  {/* Metrics */}
                  <div className="grid grid-cols-2 gap-4 pt-4 border-t border-gray-100">
                    <div>
                      <p className="text-xs text-gray-500">Total Lag</p>
                      <div className="flex items-baseline gap-2 mt-1">
                        <p className="text-lg font-semibold text-gray-900">
                          {group.lag_stats.total_lag.toLocaleString()}
                        </p>
                        <Badge color={lagLevel.color}>
                          {lagLevel.label}
                        </Badge>
                      </div>
                    </div>
                    <div>
                      <p className="text-xs text-gray-500">Cluster</p>
                      <p className="text-sm font-medium text-gray-700 mt-1 truncate">
                        {clusters.find((c) => c.cluster_id === group.cluster_id)?.name || group.cluster_id}
                      </p>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Empty State */}
      {filteredGroups.length === 0 && (
        <Card>
          <CardContent className="py-12 text-center">
            <Users className="mx-auto h-12 w-12 text-gray-400" />
            <h3 className="mt-4 text-lg font-medium text-gray-900">
              No consumer groups found
            </h3>
            <p className="mt-2 text-sm text-gray-500">
              {searchQuery || stateFilter.length > 0 || lagThreshold
                ? "Try adjusting your filters"
                : "No consumer groups are currently active on this cluster"}
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
