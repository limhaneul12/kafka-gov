import { useTranslation } from "react-i18next";
import Button from "../../../../../components/ui/Button";
import { BasicConfigSection } from "./BasicConfigSection";
import { AdvancedConfigSection } from "./AdvancedConfigSection";
import { MetadataSection } from "./MetadataSection";
import type { SingleTopicFormData, Environment } from "../../../../Topics.types";

interface SingleTopicFormProps {
  formData: SingleTopicFormData;
  onFormDataChange: (data: Partial<SingleTopicFormData>) => void;
  onSubmit: () => void;
  loading: boolean;
}

export function SingleTopicForm({
  formData,
  onFormDataChange,
  onSubmit,
  loading,
}: SingleTopicFormProps) {
  const { t } = useTranslation();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit();
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <BasicConfigSection
        topicName={formData.topicName}
        partitions={formData.partitions}
        replicationFactor={formData.replicationFactor}
        environment={formData.environment}
        onTopicNameChange={(value) => onFormDataChange({ topicName: value })}
        onPartitionsChange={(value) => onFormDataChange({ partitions: value })}
        onReplicationFactorChange={(value) => onFormDataChange({ replicationFactor: value })}
        onEnvironmentChange={(value: Environment) => onFormDataChange({ environment: value })}
      />

      <div className="border-t pt-6">
        <AdvancedConfigSection
          retentionMs={formData.retentionMs}
          cleanupPolicy={formData.cleanupPolicy}
          onRetentionMsChange={(value) => onFormDataChange({ retentionMs: value })}
          onCleanupPolicyChange={(value) => onFormDataChange({ cleanupPolicy: value })}
        />
      </div>

      <div className="border-t pt-6">
        <MetadataSection
          owner={formData.owner}
          doc={formData.doc}
          tags={formData.tags}
          onOwnerChange={(value) => onFormDataChange({ owner: value })}
          onDocChange={(value) => onFormDataChange({ doc: value })}
          onTagsChange={(value) => onFormDataChange({ tags: value })}
        />
      </div>

      <div className="flex justify-end gap-2 pt-4 border-t">
        <Button type="submit" disabled={loading}>
          {loading ? t("common.loading") : t("topic.create")}
        </Button>
      </div>
    </form>
  );
}
