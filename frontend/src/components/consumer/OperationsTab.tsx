import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Card, CardContent, CardHeader, CardTitle } from "../ui/Card";
import Badge from "../ui/Badge";
import Loading from "../ui/Loading";
import type { ConsumerGroupSummary, ConsumerGroupMetrics, ConsumerPartition } from "../../types";
import FairnessGauge from "./FairnessGauge";
import { consumerAPI } from "../../services/api";

interface OperationsTabProps {
  summary: ConsumerGroupSummary;
  metrics: ConsumerGroupMetrics;
  groupId: string;
  clusterId: string;
}

interface TopicStats {
  topic: string;
  partitionCount: number;
  totalLag: number;
  avgLag: number;
  maxLag: number;
}

export default function OperationsTab({
  summary,
  metrics,
  groupId,
  clusterId,
}: OperationsTabProps) {
  const [topicStats, setTopicStats] = useState<TopicStats[]>([]);
  const [loadingTopics, setLoadingTopics] = useState(true);

  useEffect(() => {
    loadPartitionsAndCalculateStats();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [groupId, clusterId]);

  const loadPartitionsAndCalculateStats = async () => {
    try {
      setLoadingTopics(true);
      const response = await consumerAPI.getPartitions(clusterId, groupId);
      const partitionsData = response.data || [];

      // Calculate topic-level statistics
      const topicMap = new Map<string, ConsumerPartition[]>();
      partitionsData.forEach((p: ConsumerPartition) => {
        if (!topicMap.has(p.topic)) {
          topicMap.set(p.topic, []);
        }
        topicMap.get(p.topic)!.push(p);
      });

      const stats: TopicStats[] = Array.from(topicMap.entries()).map(
        ([topic, parts]) => {
          const lags = parts.map((p) => p.lag || 0);
          return {
            topic,
            partitionCount: parts.length,
            totalLag: lags.reduce((sum, lag) => sum + lag, 0),
            avgLag: lags.reduce((sum, lag) => sum + lag, 0) / lags.length,
            maxLag: Math.max(...lags),
          };
        }
      );

      // Sort by total lag descending
      stats.sort((a, b) => b.totalLag - a.totalLag);
      setTopicStats(stats);
    } catch (error) {
      console.error("Failed to load partitions:", error);
      toast.error("Failed to load topic statistics");
    } finally {
      setLoadingTopics(false);
    }
  };

  const getLagColor = (lag: number) => {
    if (lag === 0) return "emerald";
    if (lag < 1000) return "blue";
    if (lag < 5000) return "yellow";
    return "rose";
  };

  return (
    <div className="space-y-6">
      {/* Lag Statistics */}
      <Card>
        <CardHeader>
          <CardTitle>Lag Statistics</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-4">
            <div>
              <p className="text-sm text-gray-600">Total Lag</p>
              <p className="mt-2 text-2xl font-bold text-gray-900">
                {summary.lag.total.toLocaleString()}
              </p>
            </div>
            <div>
              <p className="text-sm text-gray-600">P50 Lag</p>
              <p className="mt-2 text-2xl font-bold text-gray-900">
                {summary.lag.p50.toLocaleString()}
              </p>
            </div>
            <div>
              <p className="text-sm text-gray-600">P95 Lag</p>
              <p className="mt-2 text-2xl font-bold text-gray-900">
                {summary.lag.p95.toLocaleString()}
              </p>
            </div>
            <div>
              <p className="text-sm text-gray-600">Max Lag</p>
              <p className="mt-2 text-2xl font-bold text-rose-600">
                {summary.lag.max.toLocaleString()}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Fairness & Rebalance - Combined */}
      <Card>
        <CardHeader>
          <CardTitle>Fairness & Stability Metrics</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-8 md:grid-cols-2">
            {/* Fairness Index */}
            <div className="space-y-4">
              <h3 className="text-sm font-semibold text-gray-700 border-b pb-2">
                Fairness Index
              </h3>
              <FairnessGauge
                gini={summary.fairness_gini}
                memberCount={metrics.fairness.member_count}
                avgPartitions={metrics.fairness.avg_tp_per_member}
                maxPartitions={metrics.fairness.max_tp_per_member}
                minPartitions={metrics.fairness.min_tp_per_member}
              />
            </div>

            {/* Rebalance Stability */}
            <div className="space-y-4">
              <h3 className="text-sm font-semibold text-gray-700 border-b pb-2">
                Rebalance Stability
              </h3>
              <div>
                <p className="text-sm text-gray-600">Stability Score</p>
                <div className="mt-2 flex items-baseline gap-2">
                  <p className="text-3xl font-bold text-gray-900">
                    {summary.rebalance_score !== null 
                      ? summary.rebalance_score.toFixed(1) 
                      : 'N/A'}
                  </p>
                  {summary.rebalance_score !== null && (
                    <span className="text-sm text-gray-500">/ 100</span>
                  )}
                </div>
              </div>
              {metrics.rebalance_score && (
                <>
                  <div className="grid grid-cols-2 gap-4 pt-4 border-t">
                    <div>
                      <p className="text-xs text-gray-600">Rebalances/Hour</p>
                      <p className="mt-1 text-lg font-semibold text-gray-900">
                        {metrics.rebalance_score.rebalances_per_hour.toFixed(2)}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-600">Stable Ratio</p>
                      <p className="mt-1 text-lg font-semibold text-gray-900">
                        {metrics.rebalance_score.stable_ratio
                          ? `${(metrics.rebalance_score.stable_ratio * 100).toFixed(1)}%`
                          : "N/A"}
                      </p>
                    </div>
                  </div>
                  <div className="pt-2">
                    <p className="text-xs text-gray-600">Window</p>
                    <Badge color="blue">{metrics.rebalance_score.window}</Badge>
                  </div>
                </>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Stuck Partitions */}
      {summary.stuck.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              Stuck Partitions
              <Badge color="rose">{summary.stuck.length}</Badge>
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
                      Lag
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      Status
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {summary.stuck.map((partition, idx) => (
                    <tr key={idx} className="hover:bg-gray-50">
                      <td className="px-4 py-3 text-sm text-gray-900">
                        {partition.topic}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-900">
                        {partition.partition}
                      </td>
                      <td className="px-4 py-3 text-sm">
                        <Badge color={getLagColor(partition.lag)}>
                          {partition.lag.toLocaleString()}
                        </Badge>
                      </td>
                      <td className="px-4 py-3 text-sm">
                        <Badge color="rose">Stuck</Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}

      {/* No Stuck Partitions */}
      {summary.stuck.length === 0 && (
        <Card>
          <CardContent className="py-8 text-center">
            <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-emerald-100 mb-4">
              <svg
                className="w-6 h-6 text-emerald-600"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M5 13l4 4L19 7"
                />
              </svg>
            </div>
            <h3 className="text-lg font-medium text-gray-900">
              All Partitions Healthy
            </h3>
            <p className="mt-2 text-sm text-gray-500">
              No stuck partitions detected in this consumer group
            </p>
          </CardContent>
        </Card>
      )}

      {/* Assignment Summary */}
      <Card>
        <CardHeader>
          <CardTitle>Partition Assignment</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-3">
            <div>
              <p className="text-sm text-gray-600">Total Members</p>
              <p className="mt-2 text-2xl font-bold text-gray-900">
                {metrics.fairness.member_count}
              </p>
            </div>
            <div>
              <p className="text-sm text-gray-600">Avg Partitions/Member</p>
              <p className="mt-2 text-2xl font-bold text-gray-900">
                {metrics.fairness.avg_tp_per_member.toFixed(1)}
              </p>
            </div>
            <div>
              <p className="text-sm text-gray-600">Distribution</p>
              <p className="mt-2 text-sm text-gray-900">
                Min: {metrics.fairness.min_tp_per_member} · Max:{" "}
                {metrics.fairness.max_tp_per_member}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Related Topics Table */}
      <Card>
        <CardHeader>
          <CardTitle>Related Topics</CardTitle>
        </CardHeader>
        <CardContent>
          {loadingTopics ? (
            <div className="flex justify-center py-8">
              <Loading />
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead>
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      Topic
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      Partitions
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      Total Lag
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      Avg Lag
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      Max Lag
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      Lag Share
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {topicStats.map((stat, idx) => {
                    const lagShare =
                      summary.lag.total > 0
                        ? (stat.totalLag / summary.lag.total) * 100
                        : 0;
                    return (
                      <tr key={idx} className="hover:bg-gray-50">
                        <td className="px-4 py-3 text-sm font-medium text-gray-900">
                          {stat.topic}
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-600">
                          {stat.partitionCount}
                        </td>
                        <td className="px-4 py-3 text-sm">
                          <Badge color={getLagColor(stat.totalLag)}>
                            {stat.totalLag.toLocaleString()}
                          </Badge>
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-600">
                          {Math.round(stat.avgLag).toLocaleString()}
                        </td>
                        <td className="px-4 py-3 text-sm">
                          <Badge color={getLagColor(stat.maxLag)}>
                            {stat.maxLag.toLocaleString()}
                          </Badge>
                        </td>
                        <td className="px-4 py-3 text-sm">
                          <div className="flex items-center gap-2">
                            <div className="flex-1 max-w-[100px]">
                              <div className="w-full bg-gray-200 rounded-full h-2">
                                <div
                                  className={`h-2 rounded-full ${
                                    lagShare > 50
                                      ? "bg-rose-500"
                                      : lagShare > 25
                                      ? "bg-yellow-500"
                                      : "bg-blue-500"
                                  }`}
                                  style={{ width: `${Math.min(lagShare, 100)}%` }}
                                />
                              </div>
                            </div>
                            <span className="text-xs text-gray-600">
                              {lagShare.toFixed(1)}%
                            </span>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
              {topicStats.length === 0 && (
                <div className="py-8 text-center text-gray-500">
                  No topics assigned to this consumer group
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
