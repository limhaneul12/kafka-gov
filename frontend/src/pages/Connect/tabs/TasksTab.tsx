import { useState, useEffect } from "react";
import { RotateCw, RefreshCw } from "lucide-react";
import { Card } from "../../../components/ui/Card";
import Button from "../../../components/ui/Button";
import Badge from "../../../components/ui/Badge";
import Loading from "../../../components/ui/Loading";
import type { ConnectorStatus } from "../Connect.types";

interface TaskDetail {
  connector: string;
  id: number;
  state: string;
  worker_id: string;
  trace?: string;
}

interface TasksTabProps {
  connectors: ConnectorStatus[];
  connectId: string;
  loading: boolean;
}

export function TasksTab({ connectors, connectId, loading }: TasksTabProps) {
  const [tasks, setTasks] = useState<TaskDetail[]>([]);
  const [tasksLoading, setTasksLoading] = useState(false);
  const [stateFilter, setStateFilter] = useState<"all" | string>("all");

  useEffect(() => {
    loadAllTasks();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [connectors]);

  const loadAllTasks = () => {
    const allTasks: TaskDetail[] = [];
    connectors.forEach((connector) => {
      if (connector.tasks) {
        connector.tasks.forEach((task) => {
          allTasks.push({
            connector: connector.name,
            id: task.id,
            state: task.state,
            worker_id: task.worker_id,
          });
        });
      }
    });
    setTasks(allTasks);
  };

  const handleRestartTask = async (connectorName: string, taskId: number) => {
    if (!confirm(`Restart task ${taskId} of connector "${connectorName}"?`)) return;

    try {
      setTasksLoading(true);
      await fetch(
        `/api/v1/connect/${connectId}/connectors/${connectorName}/tasks/${taskId}/restart`,
        { method: "POST" }
      );
      // Reload tasks after a short delay
      setTimeout(() => {
        loadAllTasks();
        setTasksLoading(false);
      }, 1000);
    } catch (error) {
      console.error("Failed to restart task:", error);
      setTasksLoading(false);
    }
  };

  const getStateBadgeVariant = (state: string): "success" | "warning" | "danger" | "default" => {
    switch (state?.toUpperCase()) {
      case "RUNNING":
        return "success";
      case "PAUSED":
        return "warning";
      case "FAILED":
        return "danger";
      default:
        return "default";
    }
  };

  const filteredTasks = tasks.filter((task) => 
    stateFilter === "all" || task.state === stateFilter
  );

  const taskStates = [...new Set(tasks.map((t) => t.state))];
  const runningTasks = tasks.filter((t) => t.state === "RUNNING").length;
  const failedTasks = tasks.filter((t) => t.state === "FAILED").length;

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid gap-6 md:grid-cols-3">
        <Card className="p-6">
          <div className="text-sm font-medium text-gray-600">Total Tasks</div>
          <div className="mt-2 text-3xl font-bold text-gray-900">{tasks.length}</div>
        </Card>
        <Card className="p-6">
          <div className="text-sm font-medium text-gray-600">Running</div>
          <div className="mt-2 text-3xl font-bold text-green-600">{runningTasks}</div>
        </Card>
        <Card className="p-6">
          <div className="text-sm font-medium text-gray-600">Failed</div>
          <div className="mt-2 text-3xl font-bold text-red-600">{failedTasks}</div>
        </Card>
      </div>

      {/* Filters */}
      <div className="flex items-center justify-between">
        <select
          value={stateFilter}
          onChange={(e) => setStateFilter(e.target.value)}
          className="px-3 py-2 border border-gray-300 rounded-lg focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        >
          <option value="all">All States</option>
          {taskStates.map((state) => (
            <option key={state} value={state}>
              {state}
            </option>
          ))}
        </select>

        <Button variant="secondary" size="sm" onClick={loadAllTasks}>
          <RefreshCw className={`h-4 w-4 ${tasksLoading ? "animate-spin" : ""}`} />
          Refresh
        </Button>
      </div>

      {/* Tasks Table */}
      <Card className="overflow-hidden">
        {loading || tasksLoading ? (
          <div className="flex items-center justify-center h-64">
            <Loading size="lg" />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">
                    Connector
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">
                    Task ID
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">
                    State
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">
                    Worker ID
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {filteredTasks.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-4 py-8 text-center text-gray-500">
                      No tasks found
                    </td>
                  </tr>
                ) : (
                  filteredTasks.map((task, idx) => (
                    <tr key={`${task.connector}-${task.id}-${idx}`} className="hover:bg-gray-50">
                      <td className="px-4 py-3 text-sm font-medium text-gray-900">
                        {task.connector}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600">{task.id}</td>
                      <td className="px-4 py-3">
                        <Badge variant={getStateBadgeVariant(task.state)}>
                          {task.state}
                        </Badge>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600">{task.worker_id}</td>
                      <td className="px-4 py-3">
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => handleRestartTask(task.connector, task.id)}
                          title="Restart Task"
                        >
                          <RotateCw className="h-4 w-4 text-blue-600" />
                        </Button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <div className="text-sm text-gray-500">
        Showing {filteredTasks.length} of {tasks.length} tasks
      </div>
    </div>
  );
}
