import { useState, useEffect } from "react";
import Button from "../ui/Button";
import { X, Upload, FileText, Plus, Info } from "lucide-react";

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
  
  // Environment & Policy 상태
  const [environment, setEnvironment] = useState<"dev" | "stg" | "prod">("dev");
  const [activePolicies, setActivePolicies] = useState<{
    naming: { name: string; version: number } | null;
    guardrail: { name: string; version: number } | null;
  }>({ naming: null, guardrail: null });
  const [policiesLoading, setPoliciesLoading] = useState(false);

  // 환경 변경 시 정책 로드
  useEffect(() => {
    if (isOpen) {
      loadActivePolicies(environment);
    }
  }, [isOpen, environment]);

  const loadActivePolicies = async (env: string) => {
    try {
      setPoliciesLoading(true);
      const response = await fetch(`/api/v1/policies/active/environment?environment=${env}`);
      if (response.ok) {
        const data = await response.json();
        setActivePolicies({
          naming: data.naming_policy ? {
            name: data.naming_policy.name,
            version: data.naming_policy.version
          } : null,
          guardrail: data.guardrail_policy ? {
            name: data.guardrail_policy.name,
            version: data.guardrail_policy.version
          } : null,
        });
      }
    } catch (error) {
      console.error("Failed to load policies:", error);
    } finally {
      setPoliciesLoading(false);
    }
  };

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
    setEnvironment("dev");
    setActivePolicies({ naming: null, guardrail: null });
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
              {/* Environment 선택 */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Environment *
                </label>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => setEnvironment("dev")}
                    className={`flex-1 px-4 py-2 rounded-lg font-medium transition-colors ${
                      environment === "dev"
                        ? "bg-blue-600 text-white"
                        : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                    }`}
                  >
                    Development
                  </button>
                  <button
                    type="button"
                    onClick={() => setEnvironment("stg")}
                    className={`flex-1 px-4 py-2 rounded-lg font-medium transition-colors ${
                      environment === "stg"
                        ? "bg-blue-600 text-white"
                        : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                    }`}
                  >
                    Staging
                  </button>
                  <button
                    type="button"
                    onClick={() => setEnvironment("prod")}
                    className={`flex-1 px-4 py-2 rounded-lg font-medium transition-colors ${
                      environment === "prod"
                        ? "bg-blue-600 text-white"
                        : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                    }`}
                  >
                    Production
                  </button>
                </div>
              </div>

              {/* 적용 중인 정책 표시 */}
              <div className="p-4 rounded-lg bg-blue-50 border border-blue-200">
                <div className="flex items-start gap-2">
                  <Info className="w-4 h-4 text-blue-600 mt-0.5 flex-shrink-0" />
                  <div className="flex-1">
                    <h3 className="text-sm font-semibold text-blue-900 mb-2">
                      {environment.toUpperCase()} 환경 정책
                    </h3>
                    {policiesLoading ? (
                      <p className="text-xs text-blue-700">정책 로딩 중...</p>
                    ) : (
                      <div className="space-y-1.5">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-medium text-blue-800">Naming:</span>
                          {activePolicies.naming ? (
                            <span className="text-xs text-blue-700">
                              {activePolicies.naming.name} (v{activePolicies.naming.version})
                            </span>
                          ) : (
                            <span className="text-xs text-gray-500 italic">정책 없음</span>
                          )}
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-medium text-blue-800">Guardrail:</span>
                          {activePolicies.guardrail ? (
                            <span className="text-xs text-blue-700">
                              {activePolicies.guardrail.name} (v{activePolicies.guardrail.version})
                            </span>
                          ) : (
                            <span className="text-xs text-gray-500 italic">정책 없음</span>
                          )}
                        </div>
                      </div>
                    )}
                    <p className="text-xs text-blue-700 mt-2">
                      💡 Dry-run 및 생성 시 위 정책이 자동으로 적용됩니다
                    </p>
                  </div>
                </div>
              </div>

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
