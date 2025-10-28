import { Activity, Play, Pause, AlertCircle } from "lucide-react";
import { Card, CardContent } from "../../../components/ui/Card";
import type { ConnectorStatus } from "../Connect.types";

interface OverviewTabProps {
  connectors: ConnectorStatus[];
  loading: boolean;
}

export function OverviewTab({ connectors }: OverviewTabProps) {
  const runningCount = connectors.filter((c) => c.state === "RUNNING").length;
  const pausedCount = connectors.filter((c) => c.state === "PAUSED").length;
  const failedCount = connectors.filter((c) => c.state === "FAILED").length;
  
  const totalTasks = connectors.reduce((sum, c) => sum + (c.tasks?.length || 0), 0);
  const sourceCount = connectors.filter((c) => c.type === "source").length;
  const sinkCount = connectors.filter((c) => c.type === "sink").length;

  return (
    <div className="space-y-6">
      {/* Metric Cards */}
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Total Connectors</p>
                <p className="mt-2 text-3xl font-bold text-gray-900">
                  {connectors.length}
                </p>
                <p className="mt-1 text-xs text-gray-500">
                  {sourceCount} source · {sinkCount} sink
                </p>
              </div>
              <div className="rounded-full bg-blue-100 p-3">
                <Activity className="h-6 w-6 text-blue-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Running</p>
                <p className="mt-2 text-3xl font-bold text-green-600">{runningCount}</p>
                <p className="mt-1 text-xs text-gray-500">
                  {connectors.length > 0 ? Math.round((runningCount / connectors.length) * 100) : 0}% of total
                </p>
              </div>
              <div className="rounded-full bg-green-100 p-3">
                <Play className="h-6 w-6 text-green-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Paused</p>
                <p className="mt-2 text-3xl font-bold text-yellow-600">{pausedCount}</p>
                <p className="mt-1 text-xs text-gray-500">
                  {pausedCount > 0 ? "Needs attention" : "All active"}
                </p>
              </div>
              <div className="rounded-full bg-yellow-100 p-3">
                <Pause className="h-6 w-6 text-yellow-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Failed</p>
                <p className="mt-2 text-3xl font-bold text-red-600">{failedCount}</p>
                <p className="mt-1 text-xs text-gray-500">
                  {failedCount > 0 ? "Requires action" : "Healthy"}
                </p>
              </div>
              <div className="rounded-full bg-red-100 p-3">
                <AlertCircle className="h-6 w-6 text-red-600" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Additional Metrics */}
      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardContent className="pt-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Task Summary</h3>
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">Total Tasks</span>
                <span className="text-lg font-bold text-gray-900">{totalTasks}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">Avg Tasks per Connector</span>
                <span className="text-lg font-bold text-gray-900">
                  {connectors.length > 0 ? (totalTasks / connectors.length).toFixed(1) : "0"}
                </span>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Health Status</h3>
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">Health Score</span>
                <span className="text-2xl font-bold text-green-600">
                  {connectors.length > 0 
                    ? Math.round(((runningCount) / connectors.length) * 100)
                    : 100}
                  /100
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div 
                  className="bg-green-600 h-2 rounded-full transition-all"
                  style={{ 
                    width: `${connectors.length > 0 ? (runningCount / connectors.length) * 100 : 0}%` 
                  }}
                />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Status by Type */}
      <Card>
        <CardContent className="pt-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Connector Type Distribution</h3>
          <div className="grid md:grid-cols-2 gap-6">
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-gray-600">Source Connectors</span>
                <span className="text-sm font-bold text-gray-900">{sourceCount}</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div 
                  className="bg-blue-600 h-2 rounded-full"
                  style={{ width: `${connectors.length > 0 ? (sourceCount / connectors.length) * 100 : 0}%` }}
                />
              </div>
            </div>
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-gray-600">Sink Connectors</span>
                <span className="text-sm font-bold text-gray-900">{sinkCount}</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div 
                  className="bg-purple-600 h-2 rounded-full"
                  style={{ width: `${connectors.length > 0 ? (sinkCount / connectors.length) * 100 : 0}%` }}
                />
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
