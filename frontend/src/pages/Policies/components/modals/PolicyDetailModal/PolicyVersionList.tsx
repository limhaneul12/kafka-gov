import { useTranslation } from "react-i18next";
import { Play, Archive, Trash2, GitCompare, CheckCircle } from "lucide-react";
import Badge from "../../../../../components/ui/Badge";
import type { PolicyVersion } from "../../../Policies.types";

interface PolicyVersionListProps {
  versions: PolicyVersion[];
  currentVersion: number;
  onVersionSelect: (version: PolicyVersion) => void;
  onActivate: (policyId: string, version: number) => void;
  onArchive: (policyId: string, version: number) => void;
  onDelete: (policyId: string, version: number) => void;
  onCompare: (version: number) => void;
}

export function PolicyVersionList({
  versions,
  currentVersion,
  onVersionSelect,
  onActivate,
  onArchive,
  onDelete,
  onCompare,
}: PolicyVersionListProps) {
  const { t } = useTranslation();

  const getStatusColor = (status: string) => {
    switch (status) {
      case "ACTIVE":
        return "green";
      case "DRAFT":
        return "yellow";
      case "ARCHIVED":
        return "gray";
      default:
        return "gray";
    }
  };

  return (
    <div className="space-y-2">
      <h3 className="text-sm font-semibold text-gray-900 mb-4">
        Version History ({versions.length})
      </h3>
      
      {versions.map((version) => (
        <div
          key={version.version}
          className={`p-4 rounded-lg border-2 transition-all ${
            version.version === currentVersion
              ? "border-blue-500 bg-blue-50"
              : "border-gray-200 hover:border-gray-300 bg-white"
          }`}
        >
          <div className="flex items-center justify-between">
            <div className="flex-1">
              <div className="flex items-center gap-3 mb-2">
                <button
                  onClick={() => onVersionSelect(version)}
                  className="text-lg font-semibold text-gray-900 hover:text-blue-600 transition-colors"
                >
                  v{version.version}
                </button>
                <Badge variant={getStatusColor(version.status)}>
                  {version.status}
                </Badge>
                {version.version === currentVersion && (
                  <CheckCircle className="h-4 w-4 text-blue-600" />
                )}
              </div>
              
              <p className="text-xs text-gray-600 mb-1">
                {new Date(version.created_at).toLocaleString()}
              </p>
              
              {version.description && (
                <p className="text-sm text-gray-700">{version.description}</p>
              )}
            </div>

            <div className="flex items-center gap-2">
              {version.status === "DRAFT" && (
                <button
                  onClick={() => onActivate(version.policy_id, version.version)}
                  className="p-2 text-green-600 hover:bg-green-50 rounded-lg transition-colors"
                  title="Activate"
                >
                  <Play className="h-4 w-4" />
                </button>
              )}
              
              {version.status === "ACTIVE" && (
                <button
                  onClick={() => onArchive(version.policy_id, version.version)}
                  className="p-2 text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
                  title="Archive"
                >
                  <Archive className="h-4 w-4" />
                </button>
              )}
              
              <button
                onClick={() => onCompare(version.version)}
                className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                title="Compare"
              >
                <GitCompare className="h-4 w-4" />
              </button>
              
              {version.status !== "ACTIVE" && (
                <button
                  onClick={() => onDelete(version.policy_id, version.version)}
                  className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                  title="Delete"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              )}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
