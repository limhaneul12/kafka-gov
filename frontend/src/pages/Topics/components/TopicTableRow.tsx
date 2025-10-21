import { useTranslation } from "react-i18next";
import { Edit, Trash2, ExternalLink } from "lucide-react";
import Badge from "../../components/ui/Badge";
import { getOwnerColor, getTagColor } from "../../utils/colors";
import { formatRetention } from "../../utils/format";
import type { Topic } from "../Topics.types";

interface TopicTableRowProps {
  topic: Topic;
  onEdit: (topic: Topic) => void;
  onDelete: (topicName: string) => void;
}

export function TopicTableRow({ topic, onEdit, onDelete }: TopicTableRowProps) {
  const { t } = useTranslation();

  const handleDelete = () => {
    if (confirm(`${t("topic.deleteConfirm", { name: topic.name })}?`)) {
      onDelete(topic.name);
    }
  };

  return (
    <tr className="hover:bg-gray-50 transition-colors">
      {/* Topic Name */}
      <td className="px-4 py-3 text-sm font-medium text-gray-900">
        {topic.name}
      </td>

      {/* Owners */}
      <td className="px-4 py-3">
        <div className="flex flex-wrap gap-1">
          {topic.owners.map((owner) => (
            <Badge key={owner} variant={getOwnerColor(owner)}>
              {owner}
            </Badge>
          ))}
        </div>
      </td>

      {/* Documentation */}
      <td className="px-4 py-3">
        {topic.doc && (
          <a
            href={topic.doc}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 text-blue-600 hover:text-blue-700 text-sm"
          >
            <ExternalLink className="h-3 w-3" />
            <span>Docs</span>
          </a>
        )}
      </td>

      {/* Tags */}
      <td className="px-4 py-3">
        <div className="flex flex-wrap gap-1">
          {topic.tags.slice(0, 3).map((tag) => (
            <Badge key={tag} variant={getTagColor(tag)}>
              {tag}
            </Badge>
          ))}
          {topic.tags.length > 3 && (
            <Badge variant="gray">+{topic.tags.length - 3}</Badge>
          )}
        </div>
      </td>

      {/* Environment */}
      <td className="px-4 py-3">
        <Badge
          variant={
            topic.environment === "prod"
              ? "red"
              : topic.environment === "stg"
              ? "yellow"
              : "blue"
          }
        >
          {topic.environment.toUpperCase()}
        </Badge>
      </td>

      {/* Partitions */}
      <td className="px-4 py-3 text-sm text-gray-600">
        {topic.partition_count}
      </td>

      {/* Replication Factor */}
      <td className="px-4 py-3 text-sm text-gray-600">
        {topic.replication_factor}
      </td>

      {/* Retention */}
      <td className="px-4 py-3 text-sm text-gray-600">
        {formatRetention(topic.retention_ms)}
      </td>

      {/* Actions */}
      <td className="px-4 py-3">
        <div className="flex items-center gap-2">
          <button
            onClick={() => onEdit(topic)}
            className="p-1.5 text-gray-400 hover:text-blue-600 rounded transition-colors"
            title={t("topic.edit")}
          >
            <Edit className="h-4 w-4" />
          </button>
          <button
            onClick={handleDelete}
            className="p-1.5 text-gray-400 hover:text-red-600 rounded transition-colors"
            title={t("topic.delete")}
          >
            <Trash2 className="h-4 w-4" />
          </button>
        </div>
      </td>
    </tr>
  );
}
