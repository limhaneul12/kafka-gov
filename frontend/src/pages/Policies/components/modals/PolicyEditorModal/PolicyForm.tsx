import { useTranslation } from "react-i18next";

interface PolicyFormProps {
  mode: "create" | "edit";
  policyType: string;
  name: string;
  description: string;
  createdBy: string;
  targetEnvironment: string;
  onPolicyTypeChange: (value: string) => void;
  onNameChange: (value: string) => void;
  onDescriptionChange: (value: string) => void;
  onCreatedByChange: (value: string) => void;
  onTargetEnvironmentChange: (value: string) => void;
}

export function PolicyForm({
  mode,
  policyType,
  name,
  description,
  createdBy,
  targetEnvironment,
  onPolicyTypeChange,
  onNameChange,
  onDescriptionChange,
  onCreatedByChange,
  onTargetEnvironmentChange,
}: PolicyFormProps) {
  const { t } = useTranslation();

  return (
    <div className="space-y-4">
      {/* Policy Type */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          {t("policy.type")} *
        </label>
        <select
          value={policyType}
          onChange={(e) => onPolicyTypeChange(e.target.value)}
          className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          disabled={mode === "edit"}
        >
          <option value="naming">Naming Policy</option>
          <option value="guardrail">Guardrail Policy</option>
        </select>
      </div>

      {/* Name */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          {t("policy.name")} *
        </label>
        <input
          type="text"
          value={name}
          onChange={(e) => onNameChange(e.target.value)}
          className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          placeholder="naming-policy-v1"
          required
        />
      </div>

      {/* Description */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Description *
        </label>
        <textarea
          value={description}
          onChange={(e) => onDescriptionChange(e.target.value)}
          className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          rows={3}
          placeholder="Describe this policy..."
          required
        />
      </div>

      {/* Target Environment */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Target Environment *
        </label>
        <select
          value={targetEnvironment}
          onChange={(e) => onTargetEnvironmentChange(e.target.value)}
          className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        >
          <option value="total">All Environments</option>
          <option value="dev">DEV</option>
          <option value="stg">STG</option>
          <option value="prod">PROD</option>
        </select>
      </div>

      {/* Created By (Create mode only) */}
      {mode === "create" && (
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Created By *
          </label>
          <input
            type="email"
            value={createdBy}
            onChange={(e) => onCreatedByChange(e.target.value)}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            placeholder="admin@example.com"
            required
          />
        </div>
      )}
    </div>
  );
}
