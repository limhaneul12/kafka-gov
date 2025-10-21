import { useTranslation } from "react-i18next";
import Loading from "../../components/ui/Loading";
import { TopicTableRow } from "./TopicTableRow";
import type { Topic } from "../Topics.types";

interface TopicTableProps {
  topics: Topic[];
  loading: boolean;
  onEdit: (topic: Topic) => void;
  onDelete: (topicName: string) => void;
}

export function TopicTable({ topics, loading, onEdit, onDelete }: TopicTableProps) {
  const { t } = useTranslation();

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loading size="lg" />
      </div>
    );
  }

  if (topics.length === 0) {
    return (
      <div className="text-center py-12 text-gray-500">
        <p>{t("topic.noTopics")}</p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead className="bg-gray-50 border-b">
          <tr>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
              {t("topic.name")}
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
              {t("topic.owner")}
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
              {t("topic.doc")}
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
              {t("topic.tags")}
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
              {t("topic.environment")}
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
              {t("topic.partitions")}
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
              {t("topic.replicationFactor")}
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
              {t("topic.retentionMs")}
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
              Actions
            </th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {topics.map((topic) => (
            <TopicTableRow
              key={topic.name}
              topic={topic}
              onEdit={onEdit}
              onDelete={onDelete}
            />
          ))}
        </tbody>
      </table>
    </div>
  );
}
