import { useTranslation } from "react-i18next";
import { X, Edit, History } from "lucide-react";
import Button from "../../../../../components/ui/Button";
import Badge from "../../../../../components/ui/Badge";
import type { PolicyVersion } from "../../../Policies.types";

interface PolicyHeaderProps {
  policy: PolicyVersion;
  onEdit: () => void;
  onClose: () => void;
  onToggleVersions: () => void;
  showVersions: boolean;
}

export function PolicyHeader({
  policy,
  onEdit,
  onClose,
  onToggleVersions,
  showVersions,
}: PolicyHeaderProps) {
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
    <div className="px-6 py-4 border-b bg-gray-50 flex items-center justify-between">
      <div className="flex items-center gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h2 className="text-xl font-bold text-gray-900">{policy.name}</h2>
            <Badge variant={getStatusColor(policy.status)}>
              {policy.status}
            </Badge>
            <Badge variant="blue">v{policy.version}</Badge>
          </div>
          <p className="text-sm text-gray-600 mt-1">{policy.description}</p>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <Button variant="secondary" onClick={onToggleVersions}>
          <History className="h-4 w-4" />
          {showVersions ? "Hide" : "Show"} Versions
        </Button>
        <Button variant="secondary" onClick={onEdit}>
          <Edit className="h-4 w-4" />
          {t("policy.edit")}
        </Button>
        <button
          onClick={onClose}
          className="p-2 text-gray-400 hover:text-gray-600 rounded-lg transition-colors"
        >
          <X className="h-5 w-5" />
        </button>
      </div>
    </div>
  );
}
