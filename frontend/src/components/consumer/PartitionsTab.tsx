import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Card, CardContent, CardHeader, CardTitle } from "../ui/Card";
import Badge from "../ui/Badge";
import Loading from "../ui/Loading";
import Button from "../ui/Button";
import { consumerAPI } from "../../services/api";
import type { ConsumerPartition } from "../../types";
import { Search, Grid3x3 } from "lucide-react";
import PartitionLagHeatmap from "./PartitionLagHeatmap";

interface PartitionsTabProps {
  groupId: string;
  clusterId: string;
}

export default function PartitionsTab({ groupId, clusterId }: PartitionsTabProps) {
  const [partitions, setPartitions] = useState<ConsumerPartition[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [sortBy, setSortBy] = useState<"lag" | "topic">("lag");
  const [showStuckOnly, setShowStuckOnly] = useState(false);
  const [showHeatmap, setShowHeatmap] = useState(false);

  useEffect(() => {
    loadPartitions();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [groupId, clusterId]);

  const loadPartitions = async () => {
    try {
      setLoading(true);
      const response = await consumerAPI.getPartitions(clusterId, groupId);
      setPartitions(response.data || []);
    } catch (error) {
      console.error("Failed to load partitions:", error);
      toast.error("Failed to load partitions");
    } finally {
      setLoading(false);
    }
  };

  const getLagColor = (lag: number | null) => {
    if (lag === null || lag === 0) return "emerald";
    if (lag < 1000) return "blue";
    if (lag < 5000) return "yellow";
    return "rose";
  };

  const isStuck = (partition: ConsumerPartition) => {
    return partition.lag !== null && partition.lag > 1000;
  };

  const filteredPartitions = partitions
    .filter((p) => {
      const matchesSearch =
        !searchQuery ||
        p.topic.toLowerCase().includes(searchQuery.toLowerCase());
      const matchesStuck = !showStuckOnly || isStuck(p);
      return matchesSearch && matchesStuck;
    })
    .sort((a, b) => {
      if (sortBy === "lag") {
        return (b.lag || 0) - (a.lag || 0);
      }
      return a.topic.localeCompare(b.topic);
    });

  if (loading) {
    return (
      <div className="flex h-48 items-center justify-center">
        <Loading />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Summary */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-gray-600">Total Partitions</p>
            <p className="mt-2 text-3xl font-bold text-gray-900">
              {partitions.length}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-gray-600">Total Lag</p>
            <p className="mt-2 text-3xl font-bold text-gray-900">
              {partitions
                .reduce((sum, p) => sum + (p.lag || 0), 0)
                .toLocaleString()}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-gray-600">Avg Lag</p>
            <p className="mt-2 text-3xl font-bold text-gray-900">
              {partitions.length > 0
                ? Math.round(
                    partitions.reduce((sum, p) => sum + (p.lag || 0), 0) /
                      partitions.length
                  ).toLocaleString()
                : 0}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-gray-600">Stuck Partitions</p>
            <p className="mt-2 text-3xl font-bold text-rose-600">
              {partitions.filter(isStuck).length}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-wrap gap-4">
            {/* Search */}
            <div className="relative flex-1 min-w-[200px]">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
              <input
                type="text"
                placeholder="Search topics..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full rounded-lg border border-gray-300 py-2 pl-10 pr-4 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>

            {/* Sort */}
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as "lag" | "topic")}
              className="rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              <option value="lag">Sort by Lag (High to Low)</option>
              <option value="topic">Sort by Topic (A-Z)</option>
            </select>

            {/* Stuck Filter */}
            <label className="flex items-center gap-2 px-4 py-2 border rounded-lg cursor-pointer hover:bg-gray-50">
              <input
                type="checkbox"
                checked={showStuckOnly}
                onChange={(e) => setShowStuckOnly(e.target.checked)}
                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <span className="text-sm text-gray-700">Stuck Only</span>
            </label>

            {/* Heatmap Toggle */}
            <Button
              variant={showHeatmap ? "primary" : "secondary"}
              onClick={() => setShowHeatmap(!showHeatmap)}
            >
              <Grid3x3 className="h-4 w-4" />
              {showHeatmap ? "Hide" : "Show"} Heatmap
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Heatmap View */}
      {showHeatmap && (
        <Card>
          <CardHeader>
            <CardTitle>Partition Lag Heatmap</CardTitle>
          </CardHeader>
          <CardContent>
            <PartitionLagHeatmap partitions={filteredPartitions} />
          </CardContent>
        </Card>
      )}

      {/* Partitions Table */}
      <Card>
        <CardHeader>
          <CardTitle>
            Partition Details ({filteredPartitions.length})
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead>
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Topic
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Partition
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Committed
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Latest
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Lag
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Assigned To
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {filteredPartitions.map((partition, idx) => (
                  <tr key={idx} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-sm text-gray-900">
                      {partition.topic}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-900">
                      {partition.partition}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-600">
                      {partition.committed_offset !== null 
                        ? partition.committed_offset.toLocaleString()
                        : <span className="text-gray-400 italic">Not Committed</span>}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-600">
                      {partition.latest_offset?.toLocaleString() ?? "N/A"}
                    </td>
                    <td className="px-4 py-3 text-sm">
                      {partition.committed_offset === null ? (
                        <Badge color="gray">No Lag</Badge>
                      ) : (
                        <Badge color={getLagColor(partition.lag)}>
                          {partition.lag?.toLocaleString() ?? "0"}
                        </Badge>
                      )}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-600 truncate max-w-xs">
                      {partition.assigned_member_id || "Unassigned"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {filteredPartitions.length === 0 && (
            <div className="py-12 text-center text-gray-500">
              No partitions found
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
