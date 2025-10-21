import { useTranslation } from "react-i18next";
import type { Environment } from "../../../../Topics.types";

interface BasicConfigSectionProps {
  topicName: string;
  partitions: string;
  replicationFactor: string;
  environment: Environment;
  onTopicNameChange: (value: string) => void;
  onPartitionsChange: (value: string) => void;
  onReplicationFactorChange: (value: string) => void;
  onEnvironmentChange: (value: Environment) => void;
}

export function BasicConfigSection({
  topicName,
  partitions,
  replicationFactor,
  environment,
  onTopicNameChange,
  onPartitionsChange,
  onReplicationFactorChange,
  onEnvironmentChange,
}: BasicConfigSectionProps) {
  const { t } = useTranslation();

  return (
    <div className="space-y-4">
      <h3 className="text-sm font-semibold text-gray-900">
        {t("topic.name")} & {t("topic.environment")}
      </h3>

      {/* Topic Name */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          {t("topic.name")} *
        </label>
        <input
          type="text"
          value={topicName}
          onChange={(e) => onTopicNameChange(e.target.value)}
          className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          placeholder="prod.orders.created"
          required
        />
      </div>

      {/* Environment */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          {t("topic.environment")} *
        </label>
        <select
          value={environment}
          onChange={(e) => onEnvironmentChange(e.target.value as Environment)}
          className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        >
          <option value="dev">DEV</option>
          <option value="stg">STG</option>
          <option value="prod">PROD</option>
        </select>
      </div>

      {/* Partitions */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          {t("topic.partitions")} *
        </label>
        <input
          type="number"
          value={partitions}
          onChange={(e) => onPartitionsChange(e.target.value)}
          className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          min="1"
          required
        />
      </div>

      {/* Replication Factor */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          {t("topic.replicationFactor")} *
        </label>
        <input
          type="number"
          value={replicationFactor}
          onChange={(e) => onReplicationFactorChange(e.target.value)}
          className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          min="1"
          required
        />
      </div>
    </div>
  );
}
