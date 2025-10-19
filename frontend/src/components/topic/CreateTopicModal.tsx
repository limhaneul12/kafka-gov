import { useState } from "react";
import Button from "../ui/Button";
import { X, Upload, FileText, Plus } from "lucide-react";

interface CreateTopicModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (clusterId: string, yamlContent: string) => Promise<void>;
  clusterId: string;
}

export default function CreateTopicModal({
  isOpen,
  onClose,
  onSubmit,
  clusterId,
}: CreateTopicModalProps) {
  const [mode, setMode] = useState<"single" | "batch">("batch"); // 단일/배치 모드
  const [yamlContent, setYamlContent] = useState("");
  const [loading, setLoading] = useState(false);
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setLoading(true);
      await onSubmit(clusterId, yamlContent);
      handleClose();
    } catch (error) {
      console.error("Failed to create topic:", error);
      alert("Failed to create topic");
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    setYamlContent("");
    setUploadedFile(null);
    setMode("batch");
    onClose();
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setUploadedFile(file);
      const reader = new FileReader();
      reader.onload = (event) => {
        const content = event.target?.result as string;
        setYamlContent(content);
      };
      reader.readAsText(file);
    }
  };

  const exampleYaml = `topics:
  - name: user.events
    partitions: 3
    replication_factor: 2
    config:
      retention.ms: 86400000
      cleanup.policy: delete
    owner: team-platform
    doc: "User event stream"
    tags:
      - events
      - production`;

  return (
    <div className="fixed inset-0 z-50 bg-black bg-opacity-50 overflow-y-auto">
      <div className="flex min-h-screen items-center justify-center p-4">
        <div className="w-full max-w-3xl rounded-lg bg-white shadow-xl my-8">
          <div className="border-b border-gray-200 p-6">
            <div className="flex items-start justify-between">
              <div>
                <h2 className="text-2xl font-bold text-gray-900">Create Topic</h2>
                <p className="mt-1 text-sm text-gray-600">
                  단일 토픽 또는 YAML로 여러 토픽을 생성합니다
                </p>
              </div>
              <button
                onClick={handleClose}
                className="rounded-lg p-2 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Tab Selector */}
            <div className="mt-4 flex gap-2">
              <button
                onClick={() => setMode("single")}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors ${
                  mode === "single"
                    ? "bg-blue-100 text-blue-700"
                    : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                }`}
              >
                <Plus className="h-4 w-4" />
                단일 생성
              </button>
              <button
                onClick={() => setMode("batch")}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors ${
                  mode === "batch"
                    ? "bg-blue-100 text-blue-700"
                    : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                }`}
              >
                <FileText className="h-4 w-4" />
                배치 생성 (YAML)
              </button>
            </div>
          </div>

          <form onSubmit={handleSubmit} className="flex flex-col max-h-[calc(90vh-80px)]">
            <div className="p-6 space-y-6 overflow-y-auto flex-1">
              {mode === "single" ? (
                <div className="space-y-4">
                  <p className="text-sm text-gray-600">
                    단일 토픽 생성은 아래 YAML 형식으로 입력하세요:
                  </p>
                  <textarea
                    value={yamlContent}
                    onChange={(e) => setYamlContent(e.target.value)}
                    className="w-full h-60 rounded-lg border border-gray-300 px-3 py-2 font-mono text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                    placeholder={`topics:
  - name: prod.orders.created
    action: create
    partitions: 6
    replication_factor: 3
    config:
      retention.ms: 604800000
      compression.type: zstd
    metadata:
      owner: team-commerce
      doc: "Order creation events"
      tags:
        - orders
        - production
      environment: prod`}
                    required
                  />
                </div>
              ) : (
                <>
                  {/* File Upload */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      YAML 파일 업로드
                    </label>
                    <div className="flex items-center gap-3">
                      <label className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-300 rounded-lg cursor-pointer hover:bg-gray-50">
                        <Upload className="h-4 w-4 text-gray-600" />
                        <span className="text-sm text-gray-700">
                          {uploadedFile ? uploadedFile.name : "파일 선택"}
                        </span>
                        <input
                          type="file"
                          accept=".yaml,.yml"
                          onChange={handleFileUpload}
                          className="hidden"
                        />
                      </label>
                      {uploadedFile && (
                        <button
                          type="button"
                          onClick={() => {
                            setUploadedFile(null);
                            setYamlContent("");
                          }}
                          className="text-sm text-red-600 hover:text-red-800"
                        >
                          제거
                        </button>
                      )}
                    </div>
                  </div>

                  {/* YAML Editor */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      YAML Configuration *
                    </label>
                    <textarea
                      value={yamlContent}
                      onChange={(e) => setYamlContent(e.target.value)}
                      className="w-full h-80 rounded-lg border border-gray-300 px-3 py-2 font-mono text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                      placeholder={exampleYaml}
                      required
                    />
                    <p className="mt-2 text-sm text-gray-500">
                      YAML 형식으로 토픽 설정을 입력하거나 위에서 파일을 업로드하세요
                    </p>
                  </div>

                  {/* Example */}
                  <div className="rounded-lg bg-gray-50 p-4">
                    <h4 className="text-sm font-medium text-gray-700 mb-2">Example:</h4>
                    <pre className="text-xs text-gray-600 overflow-x-auto">
                      {exampleYaml}
                    </pre>
                  </div>
                </>
              )}
            </div>

            <div className="border-t border-gray-200 p-6 bg-gray-50 flex-shrink-0">
              <div className="flex justify-end gap-3">
                <Button type="button" variant="secondary" onClick={handleClose}>
                  Cancel
                </Button>
                <Button type="submit" disabled={loading || !yamlContent.trim()}>
                  {loading ? "Creating..." : "Create Topic"}
                </Button>
              </div>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
