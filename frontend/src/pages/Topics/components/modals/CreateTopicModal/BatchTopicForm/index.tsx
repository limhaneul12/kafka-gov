import { useTranslation } from "react-i18next";
import Button from "../../../../../components/ui/Button";
import { FileUploader } from "./FileUploader";
import { YAMLEditor } from "./YAMLEditor";

interface BatchTopicFormProps {
  yamlContent: string;
  uploadedFiles: File[];
  loading: boolean;
  onYamlContentChange: (value: string) => void;
  onFilesChange: (files: File[]) => void;
  onFileRemove: (index: number) => void;
  onSubmit: () => void;
  onDryRun: () => void;
}

export function BatchTopicForm({
  yamlContent,
  uploadedFiles,
  loading,
  onYamlContentChange,
  onFilesChange,
  onFileRemove,
  onSubmit,
  onDryRun,
}: BatchTopicFormProps) {
  const { t } = useTranslation();

  // Load content from uploaded files
  const handleFilesChange = async (files: File[]) => {
    onFilesChange(files);
    
    if (files.length > 0) {
      const contents = await Promise.all(
        files.map(file => file.text())
      );
      const combined = contents.join('\n---\n');
      onYamlContentChange(combined);
    }
  };

  const handleFileRemove = (index: number) => {
    onFileRemove(index);
    
    // Rebuild YAML content from remaining files
    const remaining = uploadedFiles.filter((_, i) => i !== index);
    if (remaining.length === 0) {
      onYamlContentChange('');
    }
  };

  return (
    <div className="space-y-6">
      <FileUploader
        uploadedFiles={uploadedFiles}
        onFilesChange={handleFilesChange}
        onFileRemove={handleFileRemove}
      />

      <YAMLEditor
        value={yamlContent}
        onChange={onYamlContentChange}
      />

      <div className="flex justify-end gap-2 pt-4 border-t">
        <Button
          type="button"
          variant="secondary"
          onClick={onDryRun}
          disabled={loading || !yamlContent.trim()}
        >
          🔍 Dry-Run
        </Button>
        <Button
          type="button"
          onClick={onSubmit}
          disabled={loading || !yamlContent.trim()}
        >
          {loading ? t("common.loading") : t("topic.create")}
        </Button>
      </div>
    </div>
  );
}
