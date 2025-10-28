import type { ConsumerPartition } from "../../types";

interface PartitionLagHeatmapProps {
  partitions: ConsumerPartition[];
}

export default function PartitionLagHeatmap({
  partitions,
}: PartitionLagHeatmapProps) {
  // Group partitions by topic
  const topicGroups = partitions.reduce((acc, partition) => {
    if (!acc[partition.topic]) {
      acc[partition.topic] = [];
    }
    acc[partition.topic].push(partition);
    return acc;
  }, {} as Record<string, ConsumerPartition[]>);

  // Calculate color based on lag
  const getLagColor = (lag: number | null): string => {
    if (lag === null || lag === 0) return "bg-emerald-500";
    if (lag < 100) return "bg-green-400";
    if (lag < 500) return "bg-blue-400";
    if (lag < 1000) return "bg-yellow-400";
    if (lag < 5000) return "bg-orange-500";
    return "bg-rose-600";
  };

  const getLagLabel = (lag: number | null): string => {
    if (lag === null) return "N/A";
    if (lag === 0) return "0";
    if (lag < 1000) return `${lag}`;
    if (lag < 1000000) return `${(lag / 1000).toFixed(1)}K`;
    return `${(lag / 1000000).toFixed(1)}M`;
  };

  // Sort topics alphabetically
  const sortedTopics = Object.keys(topicGroups).sort();

  if (partitions.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        No partition data available
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Legend */}
      <div className="flex items-center gap-4 flex-wrap">
        <span className="text-sm font-medium text-gray-700">Lag Legend:</span>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 bg-emerald-500 rounded" />
          <span className="text-xs text-gray-600">0</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 bg-green-400 rounded" />
          <span className="text-xs text-gray-600">&lt; 100</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 bg-blue-400 rounded" />
          <span className="text-xs text-gray-600">&lt; 500</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 bg-yellow-400 rounded" />
          <span className="text-xs text-gray-600">&lt; 1K</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 bg-orange-500 rounded" />
          <span className="text-xs text-gray-600">&lt; 5K</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 bg-rose-600 rounded" />
          <span className="text-xs text-gray-600">≥ 5K</span>
        </div>
      </div>

      {/* Heatmap */}
      <div className="space-y-4">
        {sortedTopics.map((topic) => {
          const topicPartitions = topicGroups[topic].sort(
            (a, b) => a.partition - b.partition
          );
          return (
            <div key={topic} className="space-y-2">
              <h4 className="text-sm font-medium text-gray-700">{topic}</h4>
              <div className="grid gap-1" style={{
                gridTemplateColumns: `repeat(auto-fill, minmax(60px, 1fr))`,
                maxWidth: '100%'
              }}>
                {topicPartitions.map((partition) => (
                  <div
                    key={`${partition.topic}-${partition.partition}`}
                    className={`
                      ${getLagColor(partition.lag)}
                      rounded p-2 text-white text-center
                      transition-transform hover:scale-105 cursor-pointer
                      shadow-sm
                    `}
                    title={`Partition ${partition.partition}\nLag: ${
                      partition.lag?.toLocaleString() || "N/A"
                    }\nCommitted: ${
                      partition.committed_offset?.toLocaleString() || "N/A"
                    }\nLatest: ${
                      partition.latest_offset?.toLocaleString() || "N/A"
                    }\nMember: ${partition.assigned_member_id || "Unassigned"}`}
                  >
                    <div className="text-xs font-semibold">
                      P{partition.partition}
                    </div>
                    <div className="text-xs font-bold mt-1">
                      {getLagLabel(partition.lag)}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>

      {/* Summary */}
      <div className="pt-4 border-t">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
          <div>
            <p className="text-xs text-gray-600">Total Partitions</p>
            <p className="text-lg font-bold text-gray-900">{partitions.length}</p>
          </div>
          <div>
            <p className="text-xs text-gray-600">Total Topics</p>
            <p className="text-lg font-bold text-gray-900">
              {sortedTopics.length}
            </p>
          </div>
          <div>
            <p className="text-xs text-gray-600">Healthy (0 lag)</p>
            <p className="text-lg font-bold text-emerald-600">
              {partitions.filter((p) => p.lag === 0).length}
            </p>
          </div>
          <div>
            <p className="text-xs text-gray-600">High Lag (≥5K)</p>
            <p className="text-lg font-bold text-rose-600">
              {partitions.filter((p) => (p.lag || 0) >= 5000).length}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
