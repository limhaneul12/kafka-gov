import { useState, useEffect } from "react";
import { toast } from "sonner";
import Button from "../ui/Button";
import { X, Upload, FileText, Plus, Info, CheckCircle2 } from "lucide-react";

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
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([]);
  
  // Dry-run 상태
  const [dryRunResult, setDryRunResult] = useState<any | null>(null);
  const [showDryRunResult, setShowDryRunResult] = useState(false);
  const [showPolicyWarning, setShowPolicyWarning] = useState(false);
  
  // 단일 생성 Form 상태
  const [topicName, setTopicName] = useState("");
  const [partitions, setPartitions] = useState("3");
  const [replicationFactor, setReplicationFactor] = useState("2");
  const [retentionMs, setRetentionMs] = useState("604800000"); // 7일
  const [cleanupPolicy, setCleanupPolicy] = useState("delete");
  const [owner, setOwner] = useState("");
  const [doc, setDoc] = useState("");
  const [tags, setTags] = useState("");
  
  // Environment & Policy 상태
  const [environment, setEnvironment] = useState<"dev" | "stg" | "prod">("dev");
  const [activePolicies, setActivePolicies] = useState<{
    naming: { name: string; version: number } | null;
    guardrail: { name: string; version: number } | null;
  }>({ naming: null, guardrail: null });
  const [policiesLoading, setPoliciesLoading] = useState(false);

  // Config Preset 정의
  const configPresets = {
    dev: {
      partitions: "1",
      replicationFactor: "1",
      retentionMs: "86400000", // 1일
      description: "개발 환경 (작은 리소스)"
    },
    stg: {
      partitions: "3",
      replicationFactor: "2",
      retentionMs: "604800000", // 7일
      description: "스테이징 환경 (중간 리소스)"
    },
    prod: {
      partitions: "6",
      replicationFactor: "3",
      retentionMs: "2592000000", // 30일
      description: "프로덕션 환경 (큰 리소스)"
    }
  };

  // Preset 적용 함수
  const applyPreset = (env: "dev" | "stg" | "prod") => {
    const preset = configPresets[env];
    setPartitions(preset.partitions);
    setReplicationFactor(preset.replicationFactor);
    setRetentionMs(preset.retentionMs);
    toast.success(`${env.toUpperCase()} Preset 적용`, {
      description: preset.description
    });
  };

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
    
    // 단일 생성 모드: 먼저 정책 검증 수행
    if (mode === "single" && !showPolicyWarning) {
      await handleSingleTopicValidation();
      return;
    }
    
    // 배치 모드 또는 강제 실행
    try {
      setLoading(true);
      
      let finalYaml = yamlContent;
      
      // 단일 생성 모드: Form 데이터를 YAML로 변환
      if (mode === "single") {
        const tagsList = tags.split(",").map(t => t.trim()).filter(t => t);
        const timestamp = new Date().toISOString().split('T')[0];
        const singleTopicYaml = `env: ${environment}
change_id: "${timestamp}_001"
items:
  - name: ${topicName}
    action: create
    config:
      partitions: ${partitions}
      replication_factor: ${replicationFactor}
      retention_ms: ${retentionMs}
      cleanup_policy: ${cleanupPolicy}
    metadata:
      owners:
        - ${owner}
      doc: "${doc}"
      tags:${tagsList.length > 0 ? '\n' + tagsList.map(tag => `        - ${tag}`).join('\n') : ' []'}`;
        finalYaml = singleTopicYaml;
      }
      
      await onSubmit(clusterId, finalYaml);
      handleClose();
    } catch (error) {
      console.error("Failed to create topic:", error);
      toast.error("토픽 생성 실패", {
        description: error instanceof Error ? error.message : "알 수 없는 에러가 발생했습니다"
      });
    } finally {
      setLoading(false);
    }
  };

  const handleSingleTopicValidation = async () => {
    try {
      setLoading(true);
      
      // Form 데이터를 YAML로 변환
      const tagsList = tags.split(",").map(t => t.trim()).filter(t => t);
      const timestamp = new Date().toISOString().split('T')[0];
      const singleTopicYaml = `env: ${environment}
change_id: "${timestamp}_001"
items:
  - name: ${topicName}
    action: create
    config:
      partitions: ${partitions}
      replication_factor: ${replicationFactor}
      retention_ms: ${retentionMs}
      cleanup_policy: ${cleanupPolicy}
    metadata:
      owners:
        - ${owner}
      doc: "${doc}"
      tags:${tagsList.length > 0 ? '\n' + tagsList.map(tag => `        - ${tag}`).join('\n') : ' []'}`;
      
      // Dry-run으로 정책 검증
      const response = await fetch(`/api/v1/topics/batch/dry-run?cluster_id=${clusterId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ yaml_content: singleTopicYaml })
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "검증 실패");
      }
      
      const result = await response.json();
      setDryRunResult(result);
      
      // 정책 위반 체크
      const hasViolations = result.violations && result.violations.length > 0;
      
      if (hasViolations) {
        setShowPolicyWarning(true);
        toast.warning("정책 위반 발견", {
          description: `${result.violations.length}개의 정책 위반이 발견되었습니다. 확인 후 강제 실행할 수 있습니다.`
        });
      } else {
        // 정책 통과 - 바로 생성 (강제 실행 플래그 설정)
        toast.success("검증 완료", {
          description: "정책 검증을 통과했습니다. 토픽을 생성합니다."
        });
        
        // 정책 검증을 통과했으므로 바로 토픽 생성 수행
        const tagsList = tags.split(",").map(t => t.trim()).filter(t => t);
        const timestamp = new Date().toISOString().split('T')[0];
        const singleTopicYaml = `env: ${environment}
change_id: "${timestamp}_001"
items:
  - name: ${topicName}
    action: create
    config:
      partitions: ${partitions}
      replication_factor: ${replicationFactor}
      retention_ms: ${retentionMs}
      cleanup_policy: ${cleanupPolicy}
    metadata:
      owners:
        - ${owner}
      doc: "${doc}"
      tags:${tagsList.length > 0 ? '\n' + tagsList.map(tag => `        - ${tag}`).join('\n') : ' []'}`;
        
        await onSubmit(clusterId, singleTopicYaml);
        handleClose();
      }
    } catch (error) {
      console.error("Validation failed:", error);
      toast.error("검증 실패", {
        description: error instanceof Error ? error.message : "검증 중 오류가 발생했습니다"
      });
    } finally {
      setLoading(false);
    }
  };

  const handleDryRun = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setLoading(true);
      
      const response = await fetch(`/api/v1/topics/batch/dry-run?cluster_id=${clusterId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ yaml_content: yamlContent })
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Dry-run 실패");
      }
      
      const result = await response.json();
      setDryRunResult(result);
      
      // 정책 위반 체크
      const hasViolations = result.violations && result.violations.length > 0;
      
      if (hasViolations) {
        setShowPolicyWarning(true);
        toast.warning("정책 위반 발견", {
          description: `${result.violations.length}개의 정책 위반이 발견되었습니다.`
        });
      } else {
        setShowDryRunResult(true);
        toast.success("Dry-run 완료", {
          description: `${result.total_items}개 항목 검증 완료`
        });
      }
    } catch (error) {
      console.error("Dry-run failed:", error);
      toast.error("Dry-run 실패", {
        description: error instanceof Error ? error.message : "검증 중 오류가 발생했습니다"
      });
    } finally {
      setLoading(false);
    }
  };

  const handleFinalApply = async () => {
    try {
      setLoading(true);
      await onSubmit(clusterId, yamlContent);
      toast.success("토픽 생성 완료");
      handleClose();
    } catch (error) {
      console.error("Failed to create topic:", error);
      toast.error("토픽 생성 실패", {
        description: error instanceof Error ? error.message : "알 수 없는 에러가 발생했습니다"
      });
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    setYamlContent("");
    setUploadedFiles([]);
    setMode("batch");
    setEnvironment("dev");
    setActivePolicies({ naming: null, guardrail: null });
    setDryRunResult(null);
    setShowDryRunResult(false);
    setShowPolicyWarning(false);
    // Form 초기화
    setTopicName("");
    setPartitions("3");
    setReplicationFactor("2");
    setRetentionMs("604800000");
    setCleanupPolicy("delete");
    setOwner("");
    setDoc("");
    setTags("");
    onClose();
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    if (files.length === 0) return;

    setUploadedFiles(files);

    // 여러 파일의 내용을 읽어서 병합
    try {
      const contents = await Promise.all(
        files.map((file) => {
          return new Promise<string>((resolve) => {
            const reader = new FileReader();
            reader.onload = (event) => {
              resolve(event.target?.result as string);
            };
            reader.readAsText(file);
          });
        })
      );

      // 여러 YAML 파일을 하나로 병합 (간단히 연결)
      // 실제로는 YAML 파싱 후 items를 병합해야 하지만, 여기서는 텍스트만 연결
      const mergedContent = contents.join("\n---\n");
      setYamlContent(mergedContent);
    } catch (error) {
      console.error("Failed to read files:", error);
      alert("Failed to read YAML files");
    }
  };

  const exampleYaml = `env: dev
change_id: 2025-10-20_001
items:
  - name: user.events
    action: create
    config:
      partitions: 3
      replication_factor: 2
      retention_ms: 86400000
      cleanup_policy: delete
    metadata:
      owners:
        - team-platform
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
              {/* 정책 위반 경고 */}
              {showPolicyWarning && dryRunResult?.violations && dryRunResult.violations.length > 0 && (
                <div className="rounded-lg bg-orange-50 border-2 border-orange-300 p-4">
                  <div className="flex items-start gap-3">
                    <div className="flex-shrink-0">
                      <svg className="w-6 h-6 text-orange-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                      </svg>
                    </div>
                    <div className="flex-1">
                      <h3 className="text-sm font-semibold text-orange-900 mb-2">
                        ⚠️ 정책 검증 실패
                      </h3>
                      <p className="text-sm text-orange-800 mb-3">
                        토픽 생성이 정책에 위반됩니다. <strong>급한 경우 강제 실행</strong>할 수 있지만, 
                        <strong>가능하면 정책에 맞게 수정</strong>하는 것을 권장합니다.
                      </p>
                      <div className="space-y-2">
                        {dryRunResult.violations.map((v: any, idx: number) => (
                          <div key={idx} className="bg-white rounded p-3 text-sm">
                            <div className="font-medium text-gray-900 mb-1">
                              📍 {v.name || '알 수 없는 토픽'}
                            </div>
                            <div className="text-gray-700">
                              • {v.message}
                            </div>
                            {v.rule && (
                              <div className="text-xs text-gray-500 mt-1">
                                규칙: <code className="bg-gray-100 px-1 py-0.5 rounded">{v.rule}</code>
                                {v.field && ` (필드: ${v.field})`}
                              </div>
                            )}
                            {v.severity && (
                              <div className={`inline-block mt-2 px-2 py-0.5 rounded text-xs font-medium ${
                                v.severity === 'error' ? 'bg-red-100 text-red-700' :
                                v.severity === 'warning' ? 'bg-yellow-100 text-yellow-700' :
                                'bg-gray-100 text-gray-700'
                              }`}>
                                {v.severity.toUpperCase()}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              )}

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
                  {/* Config Preset 선택 */}
                  <div className="p-4 rounded-lg bg-purple-50 border border-purple-200">
                    <div className="flex items-start gap-2 mb-3">
                      <Info className="w-4 h-4 text-purple-600 mt-0.5 flex-shrink-0" />
                      <div className="flex-1">
                        <h3 className="text-sm font-semibold text-purple-900 mb-1">
                          Config Preset
                        </h3>
                        <p className="text-xs text-purple-700">
                          환경에 맞는 설정값을 자동으로 적용합니다
                        </p>
                      </div>
                    </div>
                    <div className="grid grid-cols-3 gap-2">
                      <button
                        type="button"
                        onClick={() => applyPreset("dev")}
                        className="px-3 py-2 rounded-lg bg-white border-2 border-purple-300 hover:border-purple-500 transition-colors text-left"
                      >
                        <div className="text-xs font-semibold text-purple-900">DEV</div>
                        <div className="text-xs text-purple-700 mt-1">
                          P:1 / R:1 / 1일
                        </div>
                      </button>
                      <button
                        type="button"
                        onClick={() => applyPreset("stg")}
                        className="px-3 py-2 rounded-lg bg-white border-2 border-purple-300 hover:border-purple-500 transition-colors text-left"
                      >
                        <div className="text-xs font-semibold text-purple-900">STG</div>
                        <div className="text-xs text-purple-700 mt-1">
                          P:3 / R:2 / 7일
                        </div>
                      </button>
                      <button
                        type="button"
                        onClick={() => applyPreset("prod")}
                        className="px-3 py-2 rounded-lg bg-white border-2 border-purple-300 hover:border-purple-500 transition-colors text-left"
                      >
                        <div className="text-xs font-semibold text-purple-900">PROD</div>
                        <div className="text-xs text-purple-700 mt-1">
                          P:6 / R:3 / 30일
                        </div>
                      </button>
                    </div>
                  </div>

                  {/* Topic Name */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Topic Name *
                    </label>
                    <input
                      type="text"
                      value={topicName}
                      onChange={(e) => setTopicName(e.target.value)}
                      className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                      placeholder="prod.orders.created"
                      required
                    />
                  </div>

                  {/* Partitions & Replication Factor */}
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Partitions *
                      </label>
                      <input
                        type="number"
                        min="1"
                        value={partitions}
                        onChange={(e) => setPartitions(e.target.value)}
                        className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                        required
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Replication Factor *
                      </label>
                      <input
                        type="number"
                        min="1"
                        max="5"
                        value={replicationFactor}
                        onChange={(e) => setReplicationFactor(e.target.value)}
                        className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                        required
                      />
                    </div>
                  </div>

                  {/* Config */}
                  <div className="border-t pt-4">
                    <h3 className="text-sm font-semibold text-gray-900 mb-3">Configuration</h3>
                    <div className="space-y-3">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          Retention (ms) *
                        </label>
                        <select
                          value={retentionMs}
                          onChange={(e) => setRetentionMs(e.target.value)}
                          className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                        >
                          <option value="86400000">1일 (86400000)</option>
                          <option value="259200000">3일 (259200000)</option>
                          <option value="604800000">7일 (604800000)</option>
                          <option value="1209600000">14일 (1209600000)</option>
                          <option value="2592000000">30일 (2592000000)</option>
                        </select>
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          Cleanup Policy *
                        </label>
                        <select
                          value={cleanupPolicy}
                          onChange={(e) => setCleanupPolicy(e.target.value)}
                          className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                        >
                          <option value="delete">delete</option>
                          <option value="compact">compact</option>
                        </select>
                      </div>
                    </div>
                  </div>

                  {/* Metadata */}
                  <div className="border-t pt-4">
                    <h3 className="text-sm font-semibold text-gray-900 mb-3">Metadata</h3>
                    <div className="space-y-3">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          Owner (Team) *
                        </label>
                        <input
                          type="text"
                          value={owner}
                          onChange={(e) => setOwner(e.target.value)}
                          className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                          placeholder="team-commerce"
                          required
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          Documentation *
                        </label>
                        <textarea
                          value={doc}
                          onChange={(e) => setDoc(e.target.value)}
                          rows={2}
                          className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                          placeholder="Order creation events"
                          required
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          Tags (comma-separated)
                        </label>
                        <input
                          type="text"
                          value={tags}
                          onChange={(e) => setTags(e.target.value)}
                          className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                          placeholder="orders, production, critical"
                        />
                        <p className="mt-1 text-xs text-gray-500">
                          쉼표로 구분하여 여러 태그를 입력하세요
                        </p>
                      </div>
                    </div>
                  </div>
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
                          {uploadedFiles.length > 0 
                            ? `${uploadedFiles.length}개 파일 선택됨` 
                            : "파일 선택 (다중 선택 가능)"}
                        </span>
                        <input
                          type="file"
                          accept=".yaml,.yml"
                          multiple
                          onChange={handleFileUpload}
                          className="hidden"
                        />
                      </label>
                      {uploadedFiles.length > 0 && (
                        <button
                          type="button"
                          onClick={() => {
                            setUploadedFiles([]);
                            setYamlContent("");
                          }}
                          className="text-sm text-red-600 hover:text-red-800"
                        >
                          전체 제거
                        </button>
                      )}
                    </div>
                    
                    {/* 선택된 파일 목록 */}
                    {uploadedFiles.length > 0 && (
                      <div className="mt-2">
                        <p className="text-xs font-medium text-gray-600 mb-1">선택된 파일:</p>
                        <ul className="space-y-1">
                          {uploadedFiles.map((file, index) => (
                            <li key={index} className="text-xs text-gray-500 flex items-center gap-1">
                              <FileText className="h-3 w-3" />
                              {file.name}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
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
                
                {mode === "single" ? (
                  showPolicyWarning ? (
                    <>
                      <Button 
                        type="button"
                        variant="secondary"
                        onClick={() => {
                          setShowPolicyWarning(false);
                          setDryRunResult(null);
                        }}
                      >
                        다시 수정
                      </Button>
                      <Button 
                        type="submit"
                        disabled={loading}
                        className="bg-orange-600 hover:bg-orange-700"
                      >
                        {loading ? "Creating..." : "⚠️ 강제 실행"}
                      </Button>
                    </>
                  ) : (
                    <Button 
                      type="submit" 
                      disabled={loading || !topicName.trim()}
                    >
                      {loading ? "Creating..." : "Create Topic"}
                    </Button>
                  )
                ) : (
                  <>
                    {showPolicyWarning ? (
                      <>
                        <Button 
                          type="button"
                          variant="secondary"
                          onClick={() => {
                            setShowPolicyWarning(false);
                            setDryRunResult(null);
                          }}
                        >
                          다시 수정
                        </Button>
                        <Button 
                          type="button"
                          onClick={handleFinalApply}
                          disabled={loading}
                          className="bg-orange-600 hover:bg-orange-700"
                        >
                          {loading ? "Creating..." : "⚠️ 강제 실행"}
                        </Button>
                      </>
                    ) : !showDryRunResult ? (
                      <Button 
                        type="button"
                        onClick={handleDryRun}
                        disabled={loading || !yamlContent.trim()}
                      >
                        {loading ? "Validating..." : "Dry-run"}
                      </Button>
                    ) : (
                      <Button 
                        type="button"
                        onClick={handleFinalApply}
                        disabled={loading}
                      >
                        <CheckCircle2 className="h-4 w-4" />
                        {loading ? "Creating..." : "Apply"}
                      </Button>
                    )}
                  </>
                )}
              </div>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
