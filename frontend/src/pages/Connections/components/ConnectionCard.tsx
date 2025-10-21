import { useTranslation } from "react-i18next";
import { Edit, Trash2, CheckCircle, TestTube } from "lucide-react";
import Badge from "../../../components/ui/Badge";
import Button from "../../../components/ui/Button";

interface ConnectionCardProps {
  title: string;
  subtitle: string;
  isActive: boolean;
  icon: React.ReactNode;
  onEdit: () => void;
  onDelete: () => void;
  onTest: () => void;
  onActivate: () => void;
  children?: React.ReactNode;
}

export function ConnectionCard({
  title,
  subtitle,
  isActive,
  icon,
  onEdit,
  onDelete,
  onTest,
  onActivate,
  children,
}: ConnectionCardProps) {
  const { t } = useTranslation();

  return (
    <div className={`bg-white rounded-lg border-2 p-4 transition-all ${
      isActive ? "border-green-500 bg-green-50" : "border-gray-200"
    }`}>
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-start gap-3">
          <div className={`p-2 rounded-lg ${
            isActive ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-600"
          }`}>
            {icon}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="font-semibold text-gray-900">{title}</h3>
              {isActive && (
                <Badge variant="success">
                  <CheckCircle className="h-3 w-3 mr-1" />
                  {t("connection.active")}
                </Badge>
              )}
            </div>
            <p className="text-sm text-gray-600 mt-1">{subtitle}</p>
          </div>
        </div>

        <div className="flex items-center gap-1">
          {!isActive && (
            <Button size="sm" variant="secondary" onClick={onActivate}>
              {t("connection.activate")}
            </Button>
          )}
          <button
            onClick={onTest}
            className="p-2 text-gray-400 hover:text-blue-600 rounded transition-colors"
            title={t("connection.test")}
          >
            <TestTube className="h-4 w-4" />
          </button>
          <button
            onClick={onEdit}
            className="p-2 text-gray-400 hover:text-blue-600 rounded transition-colors"
            title={t("connection.edit")}
          >
            <Edit className="h-4 w-4" />
          </button>
          <button
            onClick={onDelete}
            className="p-2 text-gray-400 hover:text-red-600 rounded transition-colors"
            title={t("connection.delete")}
          >
            <Trash2 className="h-4 w-4" />
          </button>
        </div>
      </div>

      {children && (
        <div className="mt-3 pt-3 border-t text-sm text-gray-600">
          {children}
        </div>
      )}
    </div>
  );
}
