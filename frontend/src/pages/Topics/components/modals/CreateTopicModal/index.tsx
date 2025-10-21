import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { X } from "lucide-react";
import { ModeSelector } from "./ModeSelector";
import { PolicyWarning } from "./PolicyWarning";
import { SingleTopicForm } from "./SingleTopicForm";
import { BatchTopicForm } from "./BatchTopicForm";
import { DryRunResult } from "./DryRunResult";
import type {
  CreateTopicModalProps,
  TopicMode,
  SingleTopicFormData,
  ActivePolicies,
  DryRunResult as DryRunResultType,
} from "../../../Topics.types";

export function CreateTopicModal({
  isOpen,
  onClose,
  onSubmit,
  clusterId,
}: CreateTopicModalProps) {
  const { t } = useTranslation();
  
  // Mode state
  const [mode, setMode] = useState<TopicMode>("batch");
  const [loading, setLoading] = useState(false);

  // Single topic form state
  const [singleFormData, setSingleFormData] = useState<SingleTopicFormData>({
    topicName: "",
    partitions: "3",
    replicationFactor: "2",
    retentionMs: "604800000",
    cleanupPolicy: "delete",
    owner: "",
    doc: "",
    tags: "",
    environment: "dev",
  });

  // Batch form state
  const [yamlContent, setYamlContent] = useState("");
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([]);

  // Policy state
  const [activePolicies, setActivePolicies] = useState<ActivePolicies>({
    naming: null,
    guardrail: null,
  });
  const [policiesLoading, setPoliciesLoading] = useState(false);

  // Dry-run state
  const [dryRunResult, setDryRunResult] = useState<DryRunResultType | null>(null);
  const [showDryRunResult, setShowDryRunResult] = useState(false);

  // Load active policies when environment changes
  useEffect(() => {
    if (isOpen) {
      loadActivePolicies(singleFormData.environment);
    }
  }, [isOpen, singleFormData.environment]);

  const loadActivePolicies = async (env: string) => {
    try {
      setPoliciesLoading(true);
      const response = await fetch(`/api/v1/policies/active/environment?environment=${env}`);
      if (response.ok) {
        const data = await response.json();
        setActivePolicies({
          naming: data.naming_policy
            ? { name: data.naming_policy.name, version: data.naming_policy.version }
            : null,
          guardrail: data.guardrail_policy
            ? { name: data.guardrail_policy.name, version: data.guardrail_policy.version }
            : null,
        });
      }
    } catch (error) {
      console.error("Failed to load policies:", error);
    } finally {
      setPoliciesLoading(false);
    }
  };

  const handleSingleTopicSubmit = async () => {
    // Convert single topic form to YAML
    const yaml = `kind: TopicBatch
env: ${singleFormData.environment}
change_id: "single-topic-${Date.now()}"
items:
  - name: ${singleFormData.topicName}
    action: create
    config:
      partitions: ${singleFormData.partitions}
      replication_factor: ${singleFormData.replicationFactor}
      retention_ms: ${singleFormData.retentionMs}
      cleanup_policy: "${singleFormData.cleanupPolicy}"
    metadata:
      owner: ${singleFormData.owner}
      team: ${singleFormData.owner}
      doc: "${singleFormData.doc}"
      tags: [${singleFormData.tags.split(",").map(t => `"${t.trim()}"`).join(", ")}]`;

    setLoading(true);
    try {
      await onSubmit(clusterId, yaml);
      handleClose();
    } catch (error) {
      console.error("Failed to create topic:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleBatchSubmit = async () => {
    setLoading(true);
    try {
      await onSubmit(clusterId, yamlContent);
      handleClose();
    } catch (error) {
      console.error("Failed to create topics:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleDryRun = async () => {
    // TODO: Implement dry-run API call
    console.log("Dry-run:", yamlContent);
    setDryRunResult({
      success: true,
      preview: {
        topic_name: "example.topic",
        config: { partitions: 3 },
      },
    });
    setShowDryRunResult(true);
  };

  const handleClose = () => {
    // Reset all state
    setMode("batch");
    setSingleFormData({
      topicName: "",
      partitions: "3",
      replicationFactor: "2",
      retentionMs: "604800000",
      cleanupPolicy: "delete",
      owner: "",
      doc: "",
      tags: "",
      environment: "dev",
    });
    setYamlContent("");
    setUploadedFiles([]);
    setDryRunResult(null);
    setShowDryRunResult(false);
    onClose();
  };

  if (!isOpen) return null;

  return (
    <>
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-40 p-4">
        <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col">
          {/* Header */}
          <div className="px-6 py-4 border-b flex items-center justify-between">
            <h2 className="text-xl font-bold text-gray-900">
              {t("topic.create")}
            </h2>
            <button
              onClick={handleClose}
              className="p-2 text-gray-400 hover:text-gray-600 rounded-lg transition-colors"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto p-6">
            <ModeSelector mode={mode} onChange={setMode} />

            <PolicyWarning
              environment={singleFormData.environment}
              policies={activePolicies}
              loading={policiesLoading}
            />

            {mode === "single" ? (
              <SingleTopicForm
                formData={singleFormData}
                onFormDataChange={(data) =>
                  setSingleFormData((prev) => ({ ...prev, ...data }))
                }
                onSubmit={handleSingleTopicSubmit}
                loading={loading}
              />
            ) : (
              <BatchTopicForm
                yamlContent={yamlContent}
                uploadedFiles={uploadedFiles}
                loading={loading}
                onYamlContentChange={setYamlContent}
                onFilesChange={setUploadedFiles}
                onFileRemove={(index) =>
                  setUploadedFiles((files) => files.filter((_, i) => i !== index))
                }
                onSubmit={handleBatchSubmit}
                onDryRun={handleDryRun}
              />
            )}
          </div>
        </div>
      </div>

      {/* Dry-Run Result Modal */}
      {showDryRunResult && (
        <DryRunResult
          result={dryRunResult}
          onClose={() => setShowDryRunResult(false)}
        />
      )}
    </>
  );
}
