import { useTranslation } from "react-i18next";
import { Upload, FileText, X } from "lucide-react";

interface FileUploaderProps {
  uploadedFiles: File[];
  onFilesChange: (files: File[]) => void;
  onFileRemove: (index: number) => void;
}

export function FileUploader({
  uploadedFiles,
  onFilesChange,
  onFileRemove,
}: FileUploaderProps) {
  const { t } = useTranslation();

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    onFilesChange([...uploadedFiles, ...files]);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const files = Array.from(e.dataTransfer.files);
    onFilesChange([...uploadedFiles, ...files]);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  return (
    <div className="space-y-4">
      {/* Drag & Drop Zone */}
      <div
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center hover:border-blue-400 transition-colors"
      >
        <Upload className="h-12 w-12 text-gray-400 mx-auto mb-4" />
        <p className="text-sm text-gray-600 mb-2">
          Drag & drop YAML files here
        </p>
        <p className="text-xs text-gray-500 mb-4">
          or
        </p>
        <label className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 cursor-pointer transition-colors">
          <Upload className="h-4 w-4" />
          <span>{t("schema.upload")}</span>
          <input
            type="file"
            accept=".yml,.yaml"
            multiple
            onChange={handleFileUpload}
            className="hidden"
          />
        </label>
      </div>

      {/* Uploaded Files List */}
      {uploadedFiles.length > 0 && (
        <div className="space-y-2">
          <p className="text-sm font-medium text-gray-700">
            Uploaded Files ({uploadedFiles.length})
          </p>
          {uploadedFiles.map((file, index) => (
            <div
              key={index}
              className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
            >
              <div className="flex items-center gap-3">
                <FileText className="h-5 w-5 text-gray-500" />
                <div>
                  <p className="text-sm font-medium text-gray-900">{file.name}</p>
                  <p className="text-xs text-gray-500">
                    {(file.size / 1024).toFixed(2)} KB
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => onFileRemove(index)}
                className="p-1 text-gray-400 hover:text-red-600 transition-colors"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
