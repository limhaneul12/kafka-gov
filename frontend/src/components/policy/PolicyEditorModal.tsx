import { useState, useEffect } from "react";
import Button from "../ui/Button";
import { X, FileCode, AlertCircle } from "lucide-react";

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

export default function PolicyEditorModal({
  isOpen,
  onClose,
  onSubmit,
  initialData,
  mode,
  defaultPolicyType = "naming",
}: PolicyEditorModalProps) {
  const [policyType, setPolicyType] = useState<string>(defaultPolicyType);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [contentYaml, setContentYaml] = useState("");
  const [createdBy, setCreatedBy] = useState("admin@example.com");
  const [loading, setLoading] = useState(false);
  const [yamlError, setYamlError] = useState<string | null>(null);
  const [selectedPreset, setSelectedPreset] = useState<string>("balanced");
  const [targetEnvironment, setTargetEnvironment] = useState<string>("total");

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
      description: "User-defined configuration",
      content: `preset_name: "my_custom_preset"
version: "1.0.0"
author: "platform-team"
replication_factor: 3
min_insync_replicas: 2
partitions: 12
retention_ms: 604800000
cleanup_policy: delete
description: "Custom preset for specific requirements"`
    }
  };

  useEffect(() => {
    if (!isOpen) return;
    
    if (initialData) {
      setPolicyType(initialData.policy_type);
      setName(initialData.name);
      setDescription(initialData.description || "");
      setContentYaml(JSON.stringify(initialData.content, null, 2));
      setTargetEnvironment(initialData.target_environment || "total");
    } else {
      // Create 모드: defaultPolicyType 설정
      setPolicyType(defaultPolicyType);
      setTargetEnvironment("total");
      
      // Policy Type에 맞는 기본 preset 설정
      if (defaultPolicyType === "naming") {
        setSelectedPreset("balanced");
        setContentYaml(NAMING_PRESETS.balanced.content);
      } else if (defaultPolicyType === "guardrail") {
        setSelectedPreset("prod");
        setContentYaml(GUARDRAIL_PRESETS.prod.content);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen, initialData, defaultPolicyType]);
  
  // Preset 변경 시 컨텐츠 업데이트
  useEffect(() => {
    if (initialData || !isOpen) return;
    
    if (policyType === "naming") {
      const preset = NAMING_PRESETS[selectedPreset as keyof typeof NAMING_PRESETS];
      if (preset) {
        setContentYaml(preset.content);
      }
    } else if (policyType === "guardrail") {
      const preset = GUARDRAIL_PRESETS[selectedPreset as keyof typeof GUARDRAIL_PRESETS];
      if (preset) {
        setContentYaml(preset.content);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedPreset, policyType]);

  if (!isOpen) return null;

  const parseYamlToJson = (yaml: string): Record<string, unknown> | null => {
    try {
      // JSON 형식 먼저 시도 (Edit 모드에서 JSON 표시)
      try {
        const parsed = JSON.parse(yaml);
        setYamlError(null);
        return parsed;
      } catch {
        // JSON 파싱 실패 시 YAML 파싱 시도
      }
      
      // 간단한 YAML 파서 (실제로는 js-yaml 라이브러리 사용 권장)
      const lines = yaml.split("\n").filter((line) => line.trim() && !line.trim().startsWith("#"));
      const result: Record<string, unknown> = {};
      let currentKey: string | null = null;
      let currentObject: Record<string, unknown> | null = null;
      const arrayValues: string[] = [];
      let indent = 0;

      for (const line of lines) {
        const trimmed = line.trim();
        const currentIndent = line.search(/\S/);
        
        if (trimmed.startsWith("-")) {
          // 배열 값
          const value = trimmed.substring(1).trim();
          arrayValues.push(value);
        } else if (trimmed.includes(":")) {
          // 이전 배열 처리
          if (currentKey && arrayValues.length > 0) {
            if (currentObject) {
              currentObject[currentKey] = arrayValues.slice();
            } else {
              result[currentKey] = arrayValues.slice();
            }
            arrayValues.length = 0;
          }

          const colonIndex = trimmed.indexOf(":");
          const key = trimmed.substring(0, colonIndex).trim();
          const value = trimmed.substring(colonIndex + 1).trim();
          
          // 중첩 객체 감지 (값이 없고 다음이 들여쓰기된 경우)
          if (!value || value === "") {
            // 새 객체 시작
            if (currentIndent > indent) {
              // 중첩 객체
              if (!currentObject) {
                currentObject = {};
                result[currentKey!] = currentObject;
              }
              currentKey = key;
            } else {
              // 최상위 객체
              currentKey = key;
              currentObject = null;
              indent = currentIndent;
            }
          } else {
            // 값이 있는 경우
            let parsedValue: string | number | boolean | null = value.replace(/"/g, "");
            
            // null 처리
            if (parsedValue === "null") {
              parsedValue = null;
            } 
            // boolean 처리
            else if (parsedValue === "true") {
              parsedValue = true;
            } else if (parsedValue === "false") {
              parsedValue = false;
            }
            // 숫자 변환 시도
            else {
              const numValue = Number(parsedValue);
              if (!isNaN(numValue)) {
                parsedValue = numValue;
              }
            }
            
            if (currentObject && currentIndent > indent) {
              currentObject[key] = parsedValue;
            } else {
              result[key] = parsedValue;
              currentKey = key;
            }
          }
        }
      }

      // 마지막 배열 처리
      if (currentKey && arrayValues.length > 0) {
        if (currentObject) {
          currentObject[currentKey] = arrayValues;
        } else {
          result[currentKey] = arrayValues;
        }
      }

      setYamlError(null);
      return result;
    } catch (error) {
      console.error("YAML parsing error:", error);
      setYamlError("Invalid YAML/JSON format");
      return null;
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    const content = parseYamlToJson(contentYaml);
    if (!content) {
      setYamlError("Invalid YAML format. Please check your syntax.");
      return;
    }

    try {
      setLoading(true);
      
      if (mode === "create") {
        // Create 모드: 모든 필드 전송
        await onSubmit({
          policy_type: policyType,
          name,
          description,
          content,
          created_by: createdBy,
          target_environment: targetEnvironment,
        });
      } else {
        // Edit 모드: name, description, content, target_environment 전송
        await onSubmit({
          name,
          description,
          content,
          target_environment: targetEnvironment,
        });
      }
      
      // 성공 시에만 모달 닫기
      handleClose();
    } catch (err) {
      // 에러는 상위 컴포넌트에서 Toast로 표시됨
      // 모달은 닫지 않고 유지
      console.error("Failed to submit policy:", err);
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
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 overflow-y-auto p-4">
      <div className="w-full max-w-2xl my-8 rounded-lg bg-white p-6 shadow-xl max-h-[90vh] overflow-y-auto">
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
                Target Environment *
              </label>
              <select
                value={targetEnvironment}
                onChange={(e) => setTargetEnvironment(e.target.value)}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                <option value="dev">Development (개발 전용)</option>
                <option value="stg">Staging (스테이징 전용)</option>
                <option value="prod">Production (프로덕션 전용)</option>
                <option value="total">Total (모든 환경 공통)</option>
              </select>
              <p className="mt-1 text-xs text-gray-500">
                이 정책이 적용될 환경을 선택하세요
              </p>
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

          <div className="grid gap-4 md:grid-cols-2">
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

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Description
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
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
