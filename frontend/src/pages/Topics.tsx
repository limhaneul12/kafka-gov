import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/Card";
import Button from "../components/ui/Button";
import Badge from "../components/ui/Badge";
import Loading from "../components/ui/Loading";
import Pagination from "../components/ui/Pagination";
import { topicsAPI, clustersAPI } from "../services/api";
import { Plus, RefreshCw, Trash2, Search, Edit, ExternalLink, Server } from "lucide-react";
import type { Topic, KafkaCluster } from "../types";
import EditTopicMetadataModal from "../components/topic/EditTopicMetadataModal";
import CreateTopicModal from "../components/topic/CreateTopicModal";
import MultiSelect from "../components/ui/MultiSelect";
import FailureReportModal from "../components/topic/FailureReportModal";
import SuccessReportModal from "../components/topic/SuccessReportModal";
import { promptApprovalOverride } from "../utils/approvalOverride";
import { getOwnerColor, getTagColor } from "../utils/colors";
import { formatRetention } from "../utils/format";

export default function Topics() {
  const { t } = useTranslation();
  const [topics, setTopics] = useState<Topic[]>([]);
  const [clusters, setClusters] = useState<KafkaCluster[]>([]);
  const [selectedCluster, setSelectedCluster] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [envFilter, setEnvFilter] = useState<string[]>([]);
  const [ownerFilter, setOwnerFilter] = useState<string[]>([]);
  const [tagFilter, setTagFilter] = useState<string[]>([]);
  const [selectedTopics, setSelectedTopics] = useState<string[]>([]);
  const [editingTopic, setEditingTopic] = useState<Topic | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showFailureReport, setShowFailureReport] = useState(false);
  const [showSuccessReport, setShowSuccessReport] = useState(false);
  
  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const [totalItems, setTotalItems] = useState(0);
  const [pageSize] = useState(20);
  const [failureResults, setFailureResults] = useState<Array<{
    success: boolean;
    doc: string;
    response?: {
      env: string;
      change_id: string;
      applied: string[];
      skipped?: string[];
      failed: Array<{
        topic_name: string | null;
        failure_type: string;
        error_message: string;
        suggestions: string[];
        violations?: Array<{ rule: string; message: string }>;
      }>;
      summary: Record<string, number>;
    };
  }>>([]);

  // 필터 옵션
  const allOwners = Array.from(new Set(topics.flatMap(t => t.owners)));
  const allTags = Array.from(new Set(topics.flatMap(t => t.tags)));

  const loadClusters = useCallback(async () => {
    try {
      const response = await clustersAPI.listKafka();
      setClusters(response.data);
      if (response.data.length > 0) {
        setSelectedCluster(response.data[0].cluster_id);
      }
    } catch (error) {
      console.error("Failed to load clusters:", error);
    }
  }, []);

  const loadTopics = useCallback(async (page: number = 1) => {
    if (!selectedCluster) return;

    try {
      setLoading(true);
      const response = await topicsAPI.list(selectedCluster, page, pageSize);
      // Backend는 pagination 응답을 반환 (items, total, page, size)
      setTopics(response.data.items || []);
      setTotalItems(response.data.total || 0);
    } catch (error) {
      console.error("Failed to load topics:", error);
      toast.error('토픽 조회 실패', {
        description: error instanceof Error ? error.message : '토픽 목록을 불러오는데 실패했습니다.'
      });
    } finally {
      setLoading(false);
    }
  }, [pageSize, selectedCluster]);

  useEffect(() => {
    void loadClusters();
  }, [loadClusters]);

  useEffect(() => {
    if (selectedCluster) {
      setCurrentPage(1);
    }
  }, [selectedCluster]);

  useEffect(() => {
    if (selectedCluster) {
      void loadTopics(currentPage);
    }
  }, [currentPage, loadTopics, selectedCluster]);

  const handleRefresh = async () => {
    if (!selectedCluster) {
      toast.error('클러스터 선택 필요', {
        description: '토픽을 조회할 Kafka 클러스터를 선택하세요.'
      });
      return;
    }

    try {
      toast.info('토픽 새로고침', {
        description: 'Kafka 클러스터에서 토픽 목록을 가져오는 중...'
      });
      
      await loadTopics(currentPage);
      
      toast.success('새로고침 완료', {
        description: `${topics.length}개의 토픽이 조회되었습니다.`
      });
    } catch (error) {
      console.error("Failed to refresh topics:", error);
      toast.error('새로고침 실패', {
        description: error instanceof Error ? error.message : '토픽 새로고침에 실패했습니다.'
      });
    }
  };

  const handleEditMetadata = async (data: {
    owners: string[];
    doc: string | null;
    tags: string[];
    environment: string;
    slo: string | null;
    sla: string | null;
  }) => {
    if (!editingTopic || !selectedCluster) return;

    try {
      await topicsAPI.updateMetadata(selectedCluster, editingTopic.name, data);
      await loadTopics(currentPage);
    } catch (error) {
      console.error("Failed to update topic metadata:", error);
      throw error;
    }
  };

  const handleCreateTopic = async (clusterId: string, yamlContent: string) => {
    try {
      // 여러 YAML 문서(---로 구분됨)를 개별 처리
      const documents = yamlContent.split(/\n---\n/).filter((doc) => doc.trim());
      const requiresApproval = documents.some(
        (doc) => /(^|\n)env:\s*prod\b/i.test(doc) || /(^|\n)\s*action:\s*delete\b/i.test(doc)
      );
      const approvalOverride = requiresApproval
        ? promptApprovalOverride("topic apply")
        : undefined;

      if (requiresApproval && !approvalOverride) {
        toast.error('승인 근거 필요', {
          description: '고위험 토픽 변경에는 사유, 승인자, 만료 시간이 필요합니다.'
        });
        return;
      }
      
      const results: Array<{
        success: boolean;
        doc: string;
        response?: {
          env: string;
          change_id: string;
          applied: string[];
          skipped?: string[];
          failed: Array<{
            topic_name: string | null;
            failure_type: string;
            error_message: string;
            suggestions: string[];
            violations?: Array<{ rule: string; message: string }>;
            raw_error?: string;  // 원본 에러 (디버깅용)
          }>;
          summary: Record<string, number>;
        };
      }> = [];
      
      // 각 YAML 문서를 개별적으로 Backend에 전송
        for (const doc of documents) {
          try {
          const response = await topicsAPI.createFromYAML(
            clusterId,
            doc,
            approvalOverride ?? undefined,
          );
          
          // Backend가 200을 반환해도 failed가 있으면 실패로 간주
          const hasFailures = response.data.failed && response.data.failed.length > 0;
          const isSuccess = !hasFailures;
          
          if (hasFailures) {
            console.warn('⚠️ 토픽 생성 중 실패 발생:', response.data.failed);
            response.data.failed.forEach((fail: typeof response.data.failed[0], index: number) => {
              console.error(`  [${index + 1}] ${fail.topic_name || '(파싱 실패)'}:`, {
                type: fail.failure_type,
                error: fail.error_message,
                raw_error: fail.raw_error,
                violations: fail.violations,
                suggestions: fail.suggestions
              });
            });
          }
          
          results.push({ success: isSuccess, doc, response: response.data });
        } catch (error: unknown) {
          console.error('❌ Error Response:', error);
          // Axios 에러에서 Backend 리포트 추출
          if (error && typeof error === 'object' && 'response' in error) {
            const axiosError = error as { response?: { data?: unknown; status?: number; statusText?: string } };
            
            // Backend에서 구조화된 에러를 반환한 경우
            if (axiosError.response?.data && typeof axiosError.response.data === 'object') {
              const data = axiosError.response.data as { detail?: string; [key: string]: unknown };
              
              // Backend가 FastAPI 에러 형식으로 반환한 경우
              if (data.detail) {
                results.push({
                  success: false,
                  doc,
                  response: {
                    env: 'unknown',
                    change_id: 'failed',
                    applied: [],
                    failed: [{
                      topic_name: null,
                      failure_type: 'validation_error',
                      error_message: typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail),
                      suggestions: [],
                      raw_error: JSON.stringify(data, null, 2),
                    }],
                    summary: { failed_count: 1 },
                  },
                });
              } else {
                // Backend가 구조화된 리포트를 반환한 경우
                results.push({
                  success: false,
                  doc,
                  response: data as typeof results[0]['response'],
                });
              }
            } else {
              // Backend 에러가 구조화되지 않은 경우
              const status = axiosError.response?.status || 500;
              const statusText = axiosError.response?.statusText || 'Unknown Error';
              results.push({
                success: false,
                doc,
                response: {
                  env: 'unknown',
                  change_id: 'failed',
                  applied: [],
                  failed: [{
                    topic_name: null,
                    failure_type: 'http_error',
                    error_message: `HTTP ${status}: ${statusText}`,
                    suggestions: [],
                  }],
                  summary: { failed_count: 1 },
                },
              });
            }
          } else {
            // 네트워크 에러 또는 기타 에러
            const errorMessage = error instanceof Error ? error.message : 'Unknown error';
            results.push({
              success: false,
              doc,
              response: {
                env: 'unknown',
                change_id: 'failed',
                applied: [],
                failed: [{
                  topic_name: null,
                  failure_type: 'network_error',
                  error_message: errorMessage,
                  suggestions: [],
                }],
                summary: { failed_count: 1 },
              },
            });
          }
        }
      }
      
      await loadTopics(currentPage);
      
      // 상세 리포트 생성
      const totalSuccess = results.filter(r => r.success).length;
      const totalFail = results.filter(r => !r.success).length;
      
      // 모두 성공
      if (totalFail === 0) {
        const totalApplied = results.reduce((sum, r) => sum + (r.response?.applied?.length || 0), 0);
        const totalSkipped = results.reduce((sum, r) => sum + (r.response?.skipped?.length || 0), 0);
        const totalFailed = results.reduce((sum, r) => sum + (r.response?.failed?.length || 0), 0);
        
        
        const messageParts = ['✅ 배치 처리 완료!', ''];
        
        if (totalApplied > 0) {
          messageParts.push(`✓ 생성/수정: ${totalApplied}개`);
        }
        if (totalSkipped > 0) {
          messageParts.push(`⊘ 스킵: ${totalSkipped}개 (이미 존재하거나 변경사항 없음)`);
        }
        if (totalFailed > 0) {
          messageParts.push(`✗ 실패: ${totalFailed}개`);
        }
        
        if (totalApplied === 0 && totalSkipped === 0 && totalFailed === 0) {
          messageParts.push('처리된 항목이 없습니다.');
        }
        
        // 성공 리포트 모달 표시
        setFailureResults(results);
        setShowSuccessReport(true);
        
        // Toast로도 간단히 알림
        toast.success('배치 처리 완료!', {
          description: messageParts.slice(2).join('\n'),
          duration: 7000,
        });
        return;
      }
      
      // 일부 또는 전체 실패 - 상세 리포트 생성
      const reportLines: string[] = [
        `📊 배치 처리 결과`,
        `성공: ${totalSuccess}개 | 실패: ${totalFail}개`,
        '',
        '=== 실패 상세 ===',
      ];
      
      results.forEach((result, index) => {
        if (!result.success && result.response?.failed) {
          reportLines.push(`\n[배치 ${index + 1}]`);
          result.response.failed.forEach((fail) => {
            reportLines.push(`  ❌ ${fail.topic_name || '(파싱 실패)'}`);
            reportLines.push(`     타입: ${fail.failure_type}`);
            reportLines.push(`     에러: ${fail.error_message}`);
            if (fail.suggestions && fail.suggestions.length > 0) {
              reportLines.push(`     제안: ${fail.suggestions[0]}`);
            }
          });
        }
      });
      
      // const report = reportLines.join('\n'); // Unused for now
      
      
      // 실패 리포트 모달 표시
      setFailureResults(results);
      setShowFailureReport(true);
      
      // Toast로도 간단히 알림
      toast.error('배치 처리 실패', {
        description: `${totalFail}개 배치 실패. 상세 리포트를 확인하세요.`,
        duration: 5000,
      });
      
    } catch (error) {
      console.error("Failed to create topic:", error);
      toast.error('토픽 생성 실패', {
        description: error instanceof Error ? error.message : '알 수 없는 에러가 발생했습니다.'
      });
      throw error;
    }
  };

  const handleDelete = async (topicName: string) => {
    if (!selectedCluster) return;
    
    // Toast로 확인 (삭제는 위험하므로 2단계 확인)
    toast.warning(`토픽 "${topicName}" 삭제`, {
      description: "삭제 버튼을 다시 한번 클릭하면 완전히 삭제됩니다.",
      duration: 5000,
    });

    try {
      const approvalOverride = promptApprovalOverride(`topic delete for ${topicName}`);
      if (!approvalOverride) {
        toast.error('승인 근거 필요', {
          description: '토픽 삭제에는 사유, 승인자, 만료 시간이 필요합니다.'
        });
        return;
      }

      await topicsAPI.delete(selectedCluster, topicName, approvalOverride);
      await loadTopics();
    } catch (error) {
      console.error("Failed to delete topic:", error);
      toast.error('토픽 삭제 실패', {
        description: error instanceof Error ? error.message : '삭제 중 오류가 발생했습니다.'
      });
    }
  };

  const filteredTopics = topics.filter((topic) => {
    const matchesSearch = topic.name
      .toLowerCase()
      .includes(searchQuery.toLowerCase());
    const matchesEnv = envFilter.length === 0 || envFilter.includes(topic.environment);
    const matchesOwner = ownerFilter.length === 0 || topic.owners.some(owner => ownerFilter.includes(owner));
    const matchesTag = tagFilter.length === 0 || topic.tags.some(tag => tagFilter.includes(tag));
    return matchesSearch && matchesEnv && matchesOwner && matchesTag;
  });

  const getEnvBadgeVariant = (env: string) => {
    switch (env.toLowerCase()) {
      case "prod":
        return "danger";
      case "stg":
        return "warning";
      case "dev":
        return "info";
      default:
        return "default";
    }
  };

  // 클러스터 연결 없음
  if (!loading && clusters.length === 0) {
    return (
      <div className="flex h-96 items-center justify-center">
        <div className="text-center">
          <Server className="h-16 w-16 text-gray-400 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-gray-900 mb-2">
            {t("topic.notConfigured")}
          </h2>
          <p className="text-gray-600">
            {t("topic.pleaseConfigureFirst")}
          </p>
        </div>
      </div>
    );
  }

  if (loading && !topics.length) {
    return (
      <div className="flex h-96 items-center justify-center">
        <Loading size="lg" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">{t("topic.list")}</h1>
          <p className="mt-2 text-gray-600">{t("topic.description")}</p>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={handleRefresh}>
            <RefreshCw className="h-4 w-4" />
            Refresh
          </Button>
          <Button onClick={() => setShowCreateModal(true)}>
            <Plus className="h-4 w-4" />
            Create Topic
          </Button>
        </div>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="grid gap-4 md:grid-cols-4">
            <div>
              <label htmlFor="topics-cluster" className="block text-sm font-medium text-gray-700 mb-2">
                Cluster
              </label>
              <select
                id="topics-cluster"
                value={selectedCluster}
                onChange={(e) => setSelectedCluster(e.target.value)}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                {clusters.map((cluster) => (
                  <option key={cluster.cluster_id} value={cluster.cluster_id}>
                    {cluster.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label htmlFor="topics-search" className="block text-sm font-medium text-gray-700 mb-2">
                Search
              </label>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
                <input
                  id="topics-search"
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search topics..."
                  className="w-full rounded-lg border border-gray-300 pl-10 pr-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
              </div>
            </div>

            <MultiSelect
              label="Environment"
              options={["dev", "stg", "prod"]}
              selected={envFilter}
              onChange={setEnvFilter}
              placeholder="모든 환경"
              colorScheme="blue"
            />

            <MultiSelect
              label="Team/Owner"
              options={allOwners}
              selected={ownerFilter}
              onChange={setOwnerFilter}
              placeholder="모든 팀"
              colorScheme="green"
            />

            <MultiSelect
              label="Tag"
              options={allTags}
              selected={tagFilter}
              onChange={setTagFilter}
              placeholder="모든 태그"
              colorScheme="purple"
            />
          </div>
        </CardContent>
      </Card>

      {/* Edit Metadata Modal */}
      {editingTopic && (
        <EditTopicMetadataModal
          isOpen={!!editingTopic}
          onClose={() => setEditingTopic(null)}
          onSubmit={handleEditMetadata}
          initialData={editingTopic}
        />
      )}

      {/* Topics Table */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Topics ({filteredTopics.length})</CardTitle>
            {selectedTopics.length > 0 && (
              <div className="flex items-center gap-2">
                <span className="text-sm text-gray-600">
                  {selectedTopics.length}개 선택됨
                </span>
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={async () => {
                    if (!selectedCluster) return;
                    
                    // Toast 경고
                    toast.warning(`${selectedTopics.length}개 토픽 일괄 삭제`, {
                      description: "삭제 버튼을 다시 한번 클릭하면 완전히 삭제됩니다.",
                      duration: 5000,
                    });
                    
                    try {
                      const approvalOverride = promptApprovalOverride('bulk topic delete');
                      if (!approvalOverride) {
                        toast.error('승인 근거 필요', {
                          description: '일괄 삭제에는 사유, 승인자, 만료 시간이 필요합니다.'
                        });
                        return;
                      }

                      await topicsAPI.bulkDelete(selectedCluster, selectedTopics, approvalOverride);
                      await loadTopics();
                      const count = selectedTopics.length;
                      setSelectedTopics([]);
                      toast.success('일괄 삭제 완료', {
                        description: `${count}개의 토픽이 삭제되었습니다.`
                      });
                    } catch (error) {
                      console.error('Failed to bulk delete:', error);
                      toast.error('일괄 삭제 실패', {
                        description: error instanceof Error ? error.message : '삭제 중 오류가 발생했습니다.'
                      });
                    }
                  }}
                >
                  <Trash2 className="h-4 w-4" />
                  일괄 삭제
                </Button>
                <button
                  type="button"
                  onClick={() => setSelectedTopics([])}
                  className="text-sm text-gray-500 hover:text-gray-700 underline"
                >
                  선택 해제
                </button>
              </div>
            )}
          </div>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="px-2 py-3 text-center text-sm font-medium text-gray-600">
                    <input
                      type="checkbox"
                      checked={filteredTopics.length > 0 && selectedTopics.length === filteredTopics.length}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setSelectedTopics(filteredTopics.map(t => t.name));
                        } else {
                          setSelectedTopics([]);
                        }
                      }}
                      className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">
                    Name
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">
                    Owners
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">
                    Doc
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">
                    Tags
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">
                    Partitions
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">
                    Replication
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">
                    Retention
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">
                    Environment
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">
                    SLO/SLA
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {filteredTopics.length === 0 ? (
                  <tr>
                    <td colSpan={11} className="px-4 py-8 text-center text-gray-500">
                      No topics found
                    </td>
                  </tr>
                ) : (
                  filteredTopics.map((topic) => (
                    <tr key={topic.name} className={`hover:bg-gray-50 ${ selectedTopics.includes(topic.name) ? 'bg-blue-50' : '' }`}>
                      <td className="px-2 py-3 text-center">
                        <input
                          type="checkbox"
                          checked={selectedTopics.includes(topic.name)}
                          onChange={(e) => {
                            if (e.target.checked) {
                              setSelectedTopics([...selectedTopics, topic.name]);
                            } else {
                              setSelectedTopics(selectedTopics.filter(name => name !== topic.name));
                            }
                          }}
                          className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                        />
                      </td>
                      <td className="px-4 py-3 text-sm font-medium">
                        <Link
                          to={`/topics/${encodeURIComponent(topic.name)}?cluster_id=${selectedCluster}`}
                          className="text-blue-600 hover:text-blue-800 hover:underline"
                        >
                          {topic.name}
                        </Link>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex flex-wrap gap-1">
                          {topic.owners.length > 0 ? (
                            topic.owners.map((owner) => (
                              <span
                                key={owner}
                                className={`inline-flex items-center px-2 py-0.5 rounded border text-xs font-medium ${getOwnerColor(owner)}`}
                              >
                                {owner}
                              </span>
                            ))
                          ) : (
                            <span className="text-sm text-gray-400">-</span>
                          )}
                        </div>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600">
                        {topic.doc ? (
                          <a
                            href={topic.doc}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1 text-blue-600 hover:text-blue-800 transition-colors"
                            title={topic.doc}
                          >
                            <ExternalLink className="h-4 w-4" />
                          </a>
                        ) : (
                          <span className="text-gray-400">-</span>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex flex-wrap gap-1">
                          {topic.tags.length > 0 ? (
                            topic.tags.map((tag) => (
                              <span
                                key={tag}
                                className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${getTagColor(tag)}`}
                              >
                                {tag}
                              </span>
                            ))
                          ) : (
                            <span className="text-sm text-gray-400">-</span>
                          )}
                        </div>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600">
                        {topic.partition_count || "-"}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600">
                        {topic.replication_factor || "-"}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600">
                        {formatRetention(topic.retention_ms)}
                      </td>
                      <td className="px-4 py-3">
                        <Badge variant={getEnvBadgeVariant(topic.environment)}>
                          {topic.environment.toUpperCase()}
                        </Badge>
                      </td>
                      <td className="px-4 py-3 text-xs text-gray-600">
                        {topic.slo || topic.sla ? (
                          <div className="space-y-0.5">
                            {topic.slo && (
                              <div className="text-blue-600" title={`SLO: ${topic.slo}`}>
                                📊 {topic.slo.substring(0, 20)}{topic.slo.length > 20 ? '...' : ''}
                              </div>
                            )}
                            {topic.sla && (
                              <div className="text-green-600" title={`SLA: ${topic.sla}`}>
                                📋 {topic.sla.substring(0, 20)}{topic.sla.length > 20 ? '...' : ''}
                              </div>
                            )}
                          </div>
                        ) : (
                          <span className="text-gray-400">-</span>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex gap-1">
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => setEditingTopic(topic)}
                            title="Edit metadata"
                          >
                            <Edit className="h-4 w-4 text-blue-600" />
                          </Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => handleDelete(topic.name)}
                            title="Delete topic"
                          >
                            <Trash2 className="h-4 w-4 text-red-600" />
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Pagination */}
      {filteredTopics.length > 0 && (
        <Pagination
          currentPage={currentPage}
          totalPages={Math.ceil(totalItems / pageSize)}
          totalItems={totalItems}
          pageSize={pageSize}
          onPageChange={setCurrentPage}
        />
      )}

      {/* Modals */}
      <CreateTopicModal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        onSubmit={handleCreateTopic}
        clusterId={selectedCluster}
      />

      {editingTopic && (
        <EditTopicMetadataModal
          isOpen={!!editingTopic}
          onClose={() => setEditingTopic(null)}
          onSubmit={handleEditMetadata}
          initialData={editingTopic}
        />
      )}

      {/* Failure Report Modal */}
      <FailureReportModal
        isOpen={showFailureReport}
        onClose={() => setShowFailureReport(false)}
        results={failureResults}
      />

      {/* Success Report Modal */}
      <SuccessReportModal
        isOpen={showSuccessReport}
        onClose={() => setShowSuccessReport(false)}
        results={failureResults}
      />
    </div>
  );
}
