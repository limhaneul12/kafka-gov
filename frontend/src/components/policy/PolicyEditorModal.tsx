import { useState, useEffect } from "react";
import Button from "../ui/Button";
import { X, FileCode, AlertCircle } from "lucide-react";

interface PolicyEditorModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: {
    policy_type: string;
    name: string;
    description: string;
    content: Record<string, unknown>;
    created_by: string;
  }) => Promise<void>;
  initialData?: {
    policy_type: string;
    name: string;
    description: string | null;
    content: Record<string, unknown>;
  } | null;
  mode: "create" | "edit";
}

export default function PolicyEditorModal({
  isOpen,
  onClose,
  onSubmit,
  initialData,
  mode,
}: PolicyEditorModalProps) {
  const [policyType, setPolicyType] = useState<string>("naming");
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [contentYaml, setContentYaml] = useState("");
  const [createdBy, setCreatedBy] = useState("admin@example.com");
  const [loading, setLoading] = useState(false);
  const [yamlError, setYamlError] = useState<string | null>(null);
  const [selectedPreset, setSelectedPreset] = useState<string>("balanced");

  // Naming Presets (백엔드 스키마 정확히 매칭)
  const NAMING_PRESETS = {
    permissive: {
      name: "Permissive",
      description: "Free format - Startup/Small teams",
      content: `pattern: "^[a-zA-Z0-9._-]+$"
forbidden_prefixes: []
min_length: 1
max_length: 249`
    },
    balanced: {
      name: "Balanced",
      description: "{env}.{domain}.{resource}[.{action}]",
      content: `pattern: "^(dev|stg|prod)\\.[a-z0-9]+\\.[a-z0-9._-]+$"
forbidden_prefixes:
  - tmp.
  - test.
  - debug.
  - temp.
  - scratch.
allowed_environments:
  - dev
  - stg
  - prod
min_length: 1
max_length: 249`
    },
    strict: {
      name: "Strict",
      description: "{env}.{classification}.{domain}.{resource}.{version}",
      content: `pattern: "^(dev|stg|prod)\\.(pii|public|internal)\\.[a-z0-9]+\\.[a-z0-9-]+\\.v[0-9]+$"
forbidden_prefixes:
  - tmp.
  - test.
  - debug.
  - temp.
  - scratch.
  - draft.
  - experimental.
data_classifications:
  - pii
  - public
  - internal
allowed_environments:
  - dev
  - stg
  - prod
version_pattern: v1
require_version: true
require_classification: true
min_length: 1
max_length: 249`
    },
    custom: {
      name: "Custom",
      description: "User-defined via YAML",
      content: `pattern: "^[a-z0-9.-]+$"
forbidden_prefixes: []
min_length: 1
max_length: 249
description: "Custom naming rules"
examples:
  - "example.topic.name"
author: "platform-team"
version: "1.0.0"`
    }
  };

  // Guardrail Presets (백엔드 스키마 정확히 매칭)
  const GUARDRAIL_PRESETS = {
    dev: {
      name: "Development",
      description: "Fast iteration - minimal resources",
      content: `replication_factor: 1
min_insync_replicas: null
partitions: 3
retention_ms: 86400000
cleanup_policy: delete
description: "Dev environment - minimal resources, fast iteration"`
    },
    stg: {
      name: "Staging",
      description: "Production-like configuration",
      content: `replication_factor: 2
min_insync_replicas: 1
partitions: 6
retention_ms: 259200000
cleanup_policy: delete
description: "Staging environment - production-like configuration"`
    },
    prod: {
      name: "Production",
      description: "High availability (minimum recommendation)",
      content: `replication_factor: 3
min_insync_replicas: 2
partitions: 12
retention_ms: 604800000
cleanup_policy: delete
description: "Production environment - high availability and durability (minimum recommendation)"`
    },
    custom: {
      name: "Custom",
      description: "User-defined via YAML",
      content: `preset_name: "my_custom_preset"
version: "1.0.0"
author: "platform-team"
replication_factor: 3
min_insync_replicas: 2
partitions: 12
retention_ms: 604800000
cleanup_policy: delete
description: "Custom preset for specific requirements"
metadata:
  sla_target: 99.9
  compliance:
    - SOC2
tags:
  - critical`
    }
  };

  useEffect(() => {
    if (initialData) {
      setPolicyType(initialData.policy_type);
      setName(initialData.name);
      setDescription(initialData.description || "");
      setContentYaml(JSON.stringify(initialData.content, null, 2));
    } else {
      // 기본 템플릿
      if (policyType === "naming") {
        // Naming: Preset 사용
        setContentYaml(NAMING_PRESETS[selectedPreset as keyof typeof NAMING_PRESETS].content);
      } else if (policyType === "guardrail") {
        // Guardrail: Preset 사용
        setContentYaml(GUARDRAIL_PRESETS[selectedPreset as keyof typeof GUARDRAIL_PRESETS].content);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialData, policyType, selectedPreset]);

  if (!isOpen) return null;

  const parseYamlToJson = (yaml: string): Record<string, unknown> | null => {
    try {
      // 간단한 YAML 파서 (실제로는 js-yaml 라이브러리 사용 권장)
      const lines = yaml.split("\n").filter((line) => line.trim() && !line.trim().startsWith("#"));
      const result: Record<string, unknown> = {};
      let currentKey: string | null = null;
      const arrayValues: string[] = [];

      for (const line of lines) {
        const trimmed = line.trim();
        if (trimmed.startsWith("-")) {
          // 배열 값
          arrayValues.push(trimmed.substring(1).trim());
        } else if (trimmed.includes(":")) {
          // 키:값 쌍
          if (currentKey && arrayValues.length > 0) {
            result[currentKey] = arrayValues.slice();
            arrayValues.length = 0;
          }

          const [key, value] = trimmed.split(":").map((s) => s.trim());
          currentKey = key;

          if (value) {
            // 숫자 변환 시도
            const numValue = Number(value.replace(/"/g, ""));
            result[key] = isNaN(numValue) ? value.replace(/"/g, "") : numValue;
          }
        }
      }

      if (currentKey && arrayValues.length > 0) {
        result[currentKey] = arrayValues;
      }

      setYamlError(null);
      return result;
    } catch {
      setYamlError("Invalid YAML format");
      return null;
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    const content = parseYamlToJson(contentYaml);
    if (!content) {
      alert("Invalid YAML format. Please check your syntax.");
      return;
    }

    try {
      setLoading(true);
      await onSubmit({
        policy_type: policyType,
        name,
        description,
        content,
        created_by: createdBy,
      });
      handleClose();
    } catch (err) {
      console.error("Failed to submit policy:", err);
      const errorMessage = err instanceof Error ? err.message : "Failed to save policy";
      alert(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    setName("");
    setDescription("");
    setContentYaml("");
    setYamlError(null);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 overflow-y-auto">
      <div className="w-full max-w-4xl m-4 rounded-lg bg-white p-6 shadow-xl">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-2xl font-bold text-gray-900">
            {mode === "create" ? "Create Policy" : "Edit Policy"}
          </h2>
          <button
            onClick={handleClose}
            className="rounded-lg p-2 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Policy Type *
              </label>
              <select
                value={policyType}
                onChange={(e) => setPolicyType(e.target.value)}
                disabled={mode === "edit"}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:bg-gray-100"
              >
                <option value="naming">Naming Policy</option>
                <option value="guardrail">Guardrail Policy</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Created By *
              </label>
              <input
                type="email"
                value={createdBy}
                onChange={(e) => setCreatedBy(e.target.value)}
                required
                className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                placeholder="admin@example.com"
              />
            </div>
          </div>

          {/* Naming Preset Selection */}
          {policyType === "naming" && mode === "create" && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-3">
                Naming Strategy Template
              </label>
              <div className="grid grid-cols-4 gap-2">
                {Object.entries(NAMING_PRESETS).map(([key, preset]) => (
                  <button
                    key={key}
                    type="button"
                    onClick={() => setSelectedPreset(key)}
                    className={`p-3 rounded-lg border-2 text-left transition-colors ${
                      selectedPreset === key
                        ? "border-blue-500 bg-blue-50"
                        : "border-gray-200 hover:border-gray-300"
                    }`}
                  >
                    <div className="font-medium text-sm">{preset.name}</div>
                    <div className="text-xs text-gray-600 mt-1">{preset.description}</div>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Guardrail Preset Selection */}
          {policyType === "guardrail" && mode === "create" && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-3">
                Guardrail Preset Template
              </label>
              <div className="grid grid-cols-4 gap-2">
                {Object.entries(GUARDRAIL_PRESETS).map(([key, preset]) => (
                  <button
                    key={key}
                    type="button"
                    onClick={() => setSelectedPreset(key)}
                    className={`p-3 rounded-lg border-2 text-left transition-colors ${
                      selectedPreset === key
                        ? "border-blue-500 bg-blue-50"
                        : "border-gray-200 hover:border-gray-300"
                    }`}
                  >
                    <div className="font-medium text-sm">{preset.name}</div>
                    <div className="text-xs text-gray-600 mt-1">{preset.description}</div>
                  </button>
                ))}
              </div>
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Policy Name *
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              placeholder="Production Naming Policy"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Description *
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              required
              rows={2}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              placeholder="Describe the policy purpose and rules"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2 flex items-center gap-2">
              <FileCode className="h-4 w-4" />
              Policy Content (YAML-like format) *
            </label>
            <textarea
              value={contentYaml}
              onChange={(e) => setContentYaml(e.target.value)}
              rows={15}
              className={`w-full rounded-lg border px-3 py-2 font-mono text-sm focus:outline-none focus:ring-1 ${
                yamlError
                  ? "border-red-500 focus:border-red-500 focus:ring-red-500"
                  : "border-gray-300 focus:border-blue-500 focus:ring-blue-500"
              }`}
              placeholder="Enter policy rules in YAML format"
            />
            {yamlError && (
              <div className="mt-2 flex items-center gap-2 text-sm text-red-600">
                <AlertCircle className="h-4 w-4" />
                {yamlError}
              </div>
            )}
            <p className="mt-2 text-sm text-gray-500">
              {policyType === "naming"
                ? "Define naming rules: pattern, max_length, allowed_prefixes, etc."
                : "Define guardrail rules: min/max partitions, replicas, retention, etc."}
            </p>
          </div>

          <div className="flex justify-end gap-2 pt-4 border-t">
            <Button type="button" variant="secondary" onClick={handleClose}>
              Cancel
            </Button>
            <Button type="submit" disabled={loading}>
              {loading
                ? "Saving..."
                : mode === "create"
                  ? "Create Policy"
                  : "Save Changes (New Version)"}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
