import { useState } from "react";
import Button from "../ui/Button";
import { X, Upload, File } from "lucide-react";

interface UploadSchemaModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (registryId: string, formData: FormData) => Promise<void>;
  registryId: string;
}

export default function UploadSchemaModal({
  isOpen,
  onClose,
  onSubmit,
  registryId,
}: UploadSchemaModalProps) {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const [environment, setEnvironment] = useState("dev");
  const [changeId, setChangeId] = useState("");
  const [owner, setOwner] = useState("");
  const [strategyId, setStrategyId] = useState("gov:EnvPrefixed");

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file || !changeId || !owner) {
      alert("Please fill all required fields");
      return;
    }

    try {
      setLoading(true);
      const formData = new FormData();
      formData.append("files", file);  // Backend는 list[UploadFile]을 받음
      formData.append("env", environment);
      formData.append("change_id", changeId);
      formData.append("owner", owner);
      // registry_id는 Query 파라미터로 전달 (FormData에 포함하지 않음)
      formData.append("strategy_id", strategyId);
      
      await onSubmit(registryId, formData);
      handleClose();
    } catch (error) {
      console.error("Failed to upload schema:", error);
      alert("Failed to upload schema");
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    setFile(null);
    setEnvironment("dev");
    setChangeId("");
    setOwner("");
    setStrategyId("gov:EnvPrefixed");
    setDragActive(false);
    onClose();
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black bg-opacity-50 overflow-y-auto">
      <div className="flex min-h-screen items-center justify-center p-4">
        <div className="w-full max-w-2xl rounded-lg bg-white shadow-xl my-8">
          <div className="border-b border-gray-200 p-6">
            <div className="flex items-start justify-between">
              <div>
                <h2 className="text-2xl font-bold text-gray-900">Upload Schema</h2>
                <p className="mt-1 text-sm text-gray-600">
                  Avro 스키마 파일을 업로드합니다
                </p>
              </div>
              <button
                onClick={handleClose}
                className="rounded-lg p-2 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
          </div>

          <form onSubmit={handleSubmit}>
            <div className="p-6 space-y-6">
              {/* Required Fields */}
              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Environment *
                  </label>
                  <select
                    value={environment}
                    onChange={(e) => setEnvironment(e.target.value)}
                    required
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  >
                    <option value="dev">Development</option>
                    <option value="stg">Staging</option>
                    <option value="prod">Production</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Naming Strategy *
                  </label>
                  <select
                    value={strategyId}
                    onChange={(e) => setStrategyId(e.target.value)}
                    required
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  >
                    <optgroup label="SR Built-in">
                      <option value="builtin:TopicNameStrategy">Topic Name (topic-key/value)</option>
                      <option value="builtin:RecordNameStrategy">Record Name (namespace.record)</option>
                      <option value="builtin:TopicRecordNameStrategy">Topic+Record (topic-namespace.record)</option>
                    </optgroup>
                    <optgroup label="Kafka-Gov Extended">
                      <option value="gov:EnvPrefixed">Env Prefixed (env.namespace-value)</option>
                      <option value="gov:TeamScoped">Team Scoped (team.namespace.record)</option>
                      <option value="gov:CompactRecord">Compact Record (record)</option>
                    </optgroup>
                  </select>
                </div>
              </div>
              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Change ID *
                  </label>
                  <input
                    type="text"
                    value={changeId}
                    onChange={(e) => setChangeId(e.target.value)}
                    required
                    placeholder="e.g., CHG-2024-001"
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Owner/Team *
                  </label>
                  <input
                    type="text"
                    value={owner}
                    onChange={(e) => setOwner(e.target.value)}
                    required
                    placeholder="e.g., data-team"
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                </div>
              </div>
              {/* File Upload Area */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-3">
                  Schema File *
                </label>
                <div
                  className={`relative rounded-lg border-2 border-dashed p-8 text-center transition-colors ${
                    dragActive
                      ? "border-blue-500 bg-blue-50"
                      : "border-gray-300 hover:border-gray-400"
                  }`}
                  onDragEnter={handleDrag}
                  onDragLeave={handleDrag}
                  onDragOver={handleDrag}
                  onDrop={handleDrop}
                >
                  <input
                    type="file"
                    id="file-upload"
                    className="hidden"
                    accept=".avsc,.json"
                    onChange={handleFileChange}
                  />
                  
                  {file ? (
                    <div className="space-y-3">
                      <div className="flex items-center justify-center">
                        <File className="h-12 w-12 text-green-500" />
                      </div>
                      <div>
                        <p className="text-sm font-medium text-gray-900">{file.name}</p>
                        <p className="text-xs text-gray-500">
                          {(file.size / 1024).toFixed(2)} KB
                        </p>
                      </div>
                      <Button
                        type="button"
                        variant="secondary"
                        size="sm"
                        onClick={() => setFile(null)}
                      >
                        Remove
                      </Button>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      <div className="flex items-center justify-center">
                        <Upload className="h-12 w-12 text-gray-400" />
                      </div>
                      <div>
                        <label
                          htmlFor="file-upload"
                          className="cursor-pointer text-sm font-medium text-blue-600 hover:text-blue-700"
                        >
                          Choose a file
                        </label>
                        <span className="text-sm text-gray-600"> or drag and drop</span>
                      </div>
                      <p className="text-xs text-gray-500">
                        Avro schema (.avsc, .json) up to 10MB
                      </p>
                    </div>
                  )}
                </div>
              </div>

              {/* Info */}
              <div className="rounded-lg bg-blue-50 p-4">
                <h4 className="text-sm font-medium text-blue-900 mb-2">
                  Subject Naming Strategy
                </h4>
                <ul className="space-y-1 text-xs text-blue-800">
                  <li>• <strong>Topic Name:</strong> 파일명-key/value (예: orders-value)</li>
                  <li>• <strong>Record Name:</strong> 스키마의 namespace.record (예: com.company.Order)</li>
                  <li>• <strong>Env Prefixed:</strong> 환경.파일명-namespace.record (예: prod.orders-com.company.Order)</li>
                  <li>• <strong>Team Scoped:</strong> 팀.namespace.record (예: platform.com.company.Order)</li>
                </ul>
              </div>
            </div>

            <div className="border-t border-gray-200 p-6 bg-gray-50">
              <div className="flex justify-end gap-3">
                <Button type="button" variant="secondary" onClick={handleClose}>
                  Cancel
                </Button>
                <Button type="submit" disabled={loading || !file}>
                  {loading ? "Uploading..." : "Upload Schema"}
                </Button>
              </div>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
