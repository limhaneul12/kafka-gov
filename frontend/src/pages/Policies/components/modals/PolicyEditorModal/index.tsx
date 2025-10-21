import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { X } from "lucide-react";
import Button from "../../../../../components/ui/Button";
import { PolicyForm } from "./PolicyForm";
import { PresetSelector } from "./PresetSelector";
import { JSONEditor } from "./JSONEditor";
import { NAMING_PRESETS, GUARDRAIL_PRESETS } from "./presets";

interface PolicyEditorModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: {
    policy_type?: string;
    name: string;
    description: string;
    content: Record<string, unknown>;
    created_by?: string;
    target_environment?: string;
  }) => Promise<void>;
  initialData?: {
    policy_type: string;
    name: string;
    description: string | null;
    content: Record<string, unknown>;
    target_environment?: string;
  } | null;
  mode: "create" | "edit";
  defaultPolicyType?: "naming" | "guardrail";
}

export function PolicyEditorModal({
  isOpen,
  onClose,
  onSubmit,
  initialData,
  mode,
  defaultPolicyType = "naming",
}: PolicyEditorModalProps) {
  const { t } = useTranslation();
  
  const [policyType, setPolicyType] = useState<string>(defaultPolicyType);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [contentYaml, setContentYaml] = useState("");
  const [createdBy, setCreatedBy] = useState("admin@example.com");
  const [targetEnvironment, setTargetEnvironment] = useState<string>("total");
  const [selectedPreset, setSelectedPreset] = useState<string>("balanced");
  const [loading, setLoading] = useState(false);
  const [yamlError, setYamlError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen && initialData) {
      setPolicyType(initialData.policy_type);
      setName(initialData.name);
      setDescription(initialData.description || "");
      setTargetEnvironment(initialData.target_environment || "total");
      setContentYaml(JSON.stringify(initialData.content, null, 2));
    } else if (isOpen) {
      // Reset for create mode
      setPolicyType(defaultPolicyType);
      setName("");
      setDescription("");
      setContentYaml("");
      setTargetEnvironment("total");
      setSelectedPreset("balanced");
    }
  }, [isOpen, initialData, defaultPolicyType]);

  const handlePresetChange = (preset: string) => {
    setSelectedPreset(preset);
    const presets = policyType === "naming" ? NAMING_PRESETS : GUARDRAIL_PRESETS;
    setContentYaml(presets[preset].content);
    setYamlError(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setYamlError(null);

    try {
      // Parse YAML content
      const content = parseYAMLToJSON(contentYaml);

      setLoading(true);
      await onSubmit({
        ...(mode === "create" && { policy_type: policyType }),
        name,
        description,
        content,
        ...(mode === "create" && { created_by: createdBy }),
        target_environment: targetEnvironment,
      });

      onClose();
    } catch (error) {
      console.error("Failed to submit policy:", error);
      if (error instanceof Error) {
        setYamlError(error.message);
      }
    } finally {
      setLoading(false);
    }
  };

  const parseYAMLToJSON = (yaml: string): Record<string, unknown> => {
    // Simple YAML to JSON parser (for basic key: value pairs)
    try {
      const lines = yaml.split("\n");
      const result: Record<string, any> = {};
      let currentKey: string | null = null;
      let currentArray: string[] = [];

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed || trimmed.startsWith("#")) continue;

        if (trimmed.startsWith("- ")) {
          // Array item
          currentArray.push(trimmed.substring(2));
        } else if (trimmed.includes(":")) {
          // Key-value pair
          if (currentKey && currentArray.length > 0) {
            result[currentKey] = currentArray;
            currentArray = [];
          }

          const [key, ...valueParts] = trimmed.split(":");
          const value = valueParts.join(":").trim();
          currentKey = key.trim();

          if (value) {
            // Parse value type
            if (value === "true" || value === "false") {
              result[currentKey] = value === "true";
            } else if (!isNaN(Number(value))) {
              result[currentKey] = Number(value);
            } else if (value.startsWith('"') && value.endsWith('"')) {
              result[currentKey] = value.slice(1, -1);
            } else {
              result[currentKey] = value;
            }
            currentKey = null;
          }
        }
      }

      if (currentKey && currentArray.length > 0) {
        result[currentKey] = currentArray;
      }

      return result;
    } catch (error) {
      throw new Error("Invalid YAML format");
    }
  };

  if (!isOpen) return null;

  const presets = policyType === "naming" ? NAMING_PRESETS : GUARDRAIL_PRESETS;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-40 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b flex items-center justify-between">
          <h2 className="text-xl font-bold text-gray-900">
            {mode === "create" ? t("policy.create") : t("policy.edit")}
          </h2>
          <button
            onClick={onClose}
            className="p-2 text-gray-400 hover:text-gray-600 rounded-lg transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content */}
        <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto p-6 space-y-6">
          <PolicyForm
            mode={mode}
            policyType={policyType}
            name={name}
            description={description}
            createdBy={createdBy}
            targetEnvironment={targetEnvironment}
            onPolicyTypeChange={setPolicyType}
            onNameChange={setName}
            onDescriptionChange={setDescription}
            onCreatedByChange={setCreatedBy}
            onTargetEnvironmentChange={setTargetEnvironment}
          />

          {mode === "create" && (
            <PresetSelector
              policyType={policyType}
              selectedPreset={selectedPreset}
              presets={presets}
              onPresetChange={handlePresetChange}
            />
          )}

          <JSONEditor
            value={contentYaml}
            onChange={setContentYaml}
            error={yamlError}
          />

          {/* Actions */}
          <div className="flex justify-end gap-2 pt-4 border-t">
            <Button type="button" variant="secondary" onClick={onClose}>
              {t("common.cancel")}
            </Button>
            <Button type="submit" disabled={loading}>
              {loading ? t("common.loading") : t("common.save")}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
