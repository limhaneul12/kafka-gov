import { useState, useEffect } from "react";
import Button from "../ui/Button";
import Badge from "../ui/Badge";
import Loading from "../ui/Loading";
import { X, RefreshCw, RotateCcw, Settings } from "lucide-react";

interface Task {
  id: { connector: string; task: number };
  config: Record<string, string>;
}

interface TaskStatus {
  id: number;
  state: string;
  worker_id: string;
  trace?: string;
}

interface ConnectorDetail {
  name: string;
  config: Record<string, string>;
  tasks: Task[];
  type: string;
}

interface ConnectorDetailModalProps {
  isOpen: boolean;
  onClose: () => void;
  connectId: string;
  connectorName: string;
}

export default function ConnectorDetailModal({
  isOpen,
  onClose,
  connectId,
  connectorName,
}: ConnectorDetailModalProps) {
  const [connector, setConnector] = useState<ConnectorDetail | null>(null);
  const [taskStatuses, setTaskStatuses] = useState<TaskStatus[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (isOpen && connectorName) {
      loadConnector();
      loadTasks();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen, connectorName]);

  const loadConnector = async () => {
    try {
      setLoading(true);
      const response = await fetch(`/api/v1/connect/${connectId}/connectors/${connectorName}`);
      const data = await response.json();
      setConnector(data);
    } catch (error) {
      console.error("Failed to load connector:", error);
    } finally {
      setLoading(false);
    }
  };

  const loadTasks = async () => {
    try {
      const response = await fetch(
        `/api/v1/connect/${connectId}/connectors/${connectorName}/tasks`
      );
      const data = await response.json();
      setTaskStatuses(data.tasks || []);
    } catch (error) {
      console.error("Failed to load tasks:", error);
    }
  };

  const handleRestartTask = async (taskId: number) => {
    if (!confirm(`Restart task ${taskId}?`)) return;

    try {
      await fetch(
        `/api/v1/connect/${connectId}/connectors/${connectorName}/tasks/${taskId}/restart`,
        { method: "POST" }
      );
      await loadTasks();
    } catch (error) {
      console.error("Failed to restart task:", error);
      alert("Failed to restart task");
    }
  };

  const getTaskStateBadgeVariant = (state: string) => {
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

  if (!isOpen) return null;

  if (loading) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
        <div className="rounded-lg bg-white p-8">
          <Loading size="lg" />
        </div>
      </div>
    );
  }

  if (!connector) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 overflow-y-auto">
      <div className="w-full max-w-5xl m-4 rounded-lg bg-white shadow-xl">
        <div className="border-b border-gray-200 p-6">
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <div className="flex items-center gap-3 mb-2">
                <h2 className="text-2xl font-bold text-gray-900">{connector.name}</h2>
                <Badge variant="info">{connector.type}</Badge>
              </div>
              <p className="text-sm text-gray-600">Connector Configuration & Tasks</p>
            </div>
            <button
              onClick={onClose}
              className="rounded-lg p-2 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>

        <div className="p-6 space-y-6">
          {/* Configuration */}
          <div>
            <div className="flex items-center gap-2 mb-3">
              <Settings className="h-5 w-5 text-gray-600" />
              <h3 className="text-lg font-semibold text-gray-900">Configuration</h3>
            </div>
            <div className="rounded-lg bg-gray-50 p-4">
              <pre className="text-sm overflow-x-auto">
                {JSON.stringify(connector.config, null, 2)}
              </pre>
            </div>
          </div>

          {/* Tasks */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-lg font-semibold text-gray-900">
                Tasks ({taskStatuses.length})
              </h3>
              <Button size="sm" variant="secondary" onClick={loadTasks}>
                <RefreshCw className="h-4 w-4" />
                Refresh
              </Button>
            </div>

            <div className="rounded-lg border border-gray-200 overflow-hidden">
              <table className="w-full">
                <thead className="bg-gray-50">
                  <tr>
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
                      Trace
                    </th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {taskStatuses.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="px-4 py-8 text-center text-gray-500">
                        No tasks found
                      </td>
                    </tr>
                  ) : (
                    taskStatuses.map((task) => (
                      <tr key={task.id} className="hover:bg-gray-50">
                        <td className="px-4 py-3 text-sm font-medium text-gray-900">
                          {task.id}
                        </td>
                        <td className="px-4 py-3">
                          <Badge variant={getTaskStateBadgeVariant(task.state)}>
                            {task.state}
                          </Badge>
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-600">{task.worker_id}</td>
                        <td className="px-4 py-3 text-sm text-gray-600">
                          {task.trace ? (
                            <div className="max-w-md truncate" title={task.trace}>
                              {task.trace}
                            </div>
                          ) : (
                            "-"
                          )}
                        </td>
                        <td className="px-4 py-3">
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => handleRestartTask(task.id)}
                            title="Restart Task"
                          >
                            <RotateCcw className="h-4 w-4 text-blue-600" />
                          </Button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <div className="border-t border-gray-200 p-6 bg-gray-50">
          <div className="flex justify-end">
            <Button variant="secondary" onClick={onClose}>
              Close
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
