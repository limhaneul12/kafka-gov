import { useTranslation } from "react-i18next";
import { Play, Pause, RotateCw, Trash2, Eye } from "lucide-react";
import Badge from "../../../components/ui/Badge";
import type { ConnectorStatus } from "../Connect.types";

interface ConnectorCardProps {
  connector: ConnectorStatus;
  onPause: () => void;
  onResume: () => void;
  onRestart: () => void;
  onDelete: () => void;
  onViewDetails: () => void;
}

export function ConnectorCard({
  connector,
  onPause,
  onResume,
  onRestart,
  onDelete,
  onViewDetails,
}: ConnectorCardProps) {
  const { t } = useTranslation();

  const getStateColor = (state: string): "success" | "warning" | "danger" | "default" => {
    switch (state) {
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

  const getTypeColor = (type: string): "info" | "default" => {
    return type === "source" ? "info" : "default";
  };

  return (
    <div className="bg-white rounded-lg border p-4 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between mb-3">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <h3 className="font-semibold text-gray-900">{connector.name}</h3>
            <Badge variant={getStateColor(connector.state)}>
              {connector.state}
            </Badge>
            <Badge variant={getTypeColor(connector.type)}>
              {connector.type.toUpperCase()}
            </Badge>
          </div>
          <p className="text-sm text-gray-600">
            Worker: {connector.worker_id}
          </p>
        </div>

        <div className="flex items-center gap-1">
          <button
            onClick={onViewDetails}
            className="p-2 text-gray-400 hover:text-blue-600 rounded transition-colors"
            title={t("common.info")}
          >
            <Eye className="h-4 w-4" />
          </button>

          {connector.state === "RUNNING" ? (
            <button
              onClick={onPause}
              className="p-2 text-gray-400 hover:text-yellow-600 rounded transition-colors"
              title="Pause"
            >
              <Pause className="h-4 w-4" />
            </button>
          ) : (
            <button
              onClick={onResume}
              className="p-2 text-gray-400 hover:text-green-600 rounded transition-colors"
              title="Resume"
            >
              <Play className="h-4 w-4" />
            </button>
          )}

          <button
            onClick={onRestart}
            className="p-2 text-gray-400 hover:text-blue-600 rounded transition-colors"
            title="Restart"
          >
            <RotateCw className="h-4 w-4" />
          </button>

          <button
            onClick={onDelete}
            className="p-2 text-gray-400 hover:text-red-600 rounded transition-colors"
            title={t("common.delete")}
          >
            <Trash2 className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Tasks */}
      {connector.tasks && connector.tasks.length > 0 && (
        <div className="mt-3 pt-3 border-t">
          <p className="text-xs font-medium text-gray-700 mb-2">
            {t("connect.tasks")} ({connector.tasks.length})
          </p>
          <div className="flex flex-wrap gap-2">
            {connector.tasks.map((task) => (
              <div
                key={task.id}
                className="text-xs px-2 py-1 bg-gray-100 rounded"
              >
                Task {task.id}: {task.state}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
