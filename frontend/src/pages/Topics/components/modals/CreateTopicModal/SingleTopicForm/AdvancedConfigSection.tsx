import { useTranslation } from "react-i18next";

interface AdvancedConfigSectionProps {
  retentionMs: string;
  cleanupPolicy: string;
  onRetentionMsChange: (value: string) => void;
  onCleanupPolicyChange: (value: string) => void;
}

export function AdvancedConfigSection({
  retentionMs,
  cleanupPolicy,
  onRetentionMsChange,
  onCleanupPolicyChange,
}: AdvancedConfigSectionProps) {
  const { t } = useTranslation();

  // Preset retention values
  const retentionPresets = [
    { label: "1 hour", value: "3600000" },
    { label: "1 day", value: "86400000" },
    { label: "7 days", value: "604800000" },
    { label: "30 days", value: "2592000000" },
    { label: "90 days", value: "7776000000" },
  ];

  return (
    <div className="space-y-4">
      <h3 className="text-sm font-semibold text-gray-900">
        Advanced Configuration
      </h3>

      {/* Retention */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          {t("topic.retentionMs")} (ms) *
        </label>
        <div className="flex gap-2">
          <input
            type="number"
            value={retentionMs}
            onChange={(e) => onRetentionMsChange(e.target.value)}
            className="flex-1 rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            required
          />
          <select
            value={retentionMs}
            onChange={(e) => onRetentionMsChange(e.target.value)}
            className="w-32 rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            {retentionPresets.map((preset) => (
              <option key={preset.value} value={preset.value}>
                {preset.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Cleanup Policy */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Cleanup Policy *
        </label>
        <select
          value={cleanupPolicy}
          onChange={(e) => onCleanupPolicyChange(e.target.value)}
          className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        >
          <option value="delete">delete</option>
          <option value="compact">compact</option>
          <option value="compact,delete">compact,delete</option>
        </select>
        <p className="text-xs text-gray-500 mt-1">
          delete: Time-based retention | compact: Key-based deduplication
        </p>
      </div>
    </div>
  );
}
