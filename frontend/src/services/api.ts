import axios from "axios";

const api = axios.create({
  baseURL: "/api",
  headers: {
    "Content-Type": "application/json",
  },
});

// Request interceptor
api.interceptors.request.use(
  (config) => {
    // 필요 시 토큰 추가
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor
api.interceptors.response.use(
  (response) => response,
  (error) => {
    // 에러 핸들링 개선
    if (error.response) {
      // 서버가 응답했지만 에러 상태 코드
      console.error("API Error Response:", {
        status: error.response.status,
        data: error.response.data,
        url: error.config?.url,
      });
    } else if (error.request) {
      // 요청은 보냈지만 응답이 없음 (네트워크 에러, CORS 등)
      console.error("API No Response:", {
        message: error.message,
        url: error.config?.url,
        baseURL: error.config?.baseURL,
      });
    } else {
      // 요청 설정 중 에러
      console.error("API Request Setup Error:", error.message);
    }
    return Promise.reject(error);
  }
);

// API 연결 테스트 함수
export const testAPIConnection = async () => {
  try {
    const response = await api.get("");
    return { success: true, data: response.data };
  } catch (error: unknown) {
    const err = error as { message?: string; response?: { data?: unknown }; config?: { url?: string; baseURL?: string }; request?: unknown };
    console.error("❌ API Connection Failed:", err.message);
    return { 
      success: false, 
      error: err.response?.data || err.message,
      details: {
        url: err.config?.url,
        baseURL: err.config?.baseURL,
        hasResponse: !!err.response,
        hasRequest: !!err.request,
      }
    };
  }
};

export default api;

// API 엔드포인트 함수들
export const topicsAPI = {
  list: (clusterId: string, page: number = 1, size: number = 20) => 
    api.get(`/v1/topics?cluster_id=${clusterId}&page=${page}&size=${size}`),
  uploadAndDryRun: (clusterId: string, file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    return api.post(`/v1/topics/batch/upload?cluster_id=${clusterId}`, formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },
  dryRun: (clusterId: string, batchRequest: Record<string, unknown>) =>
    api.post(`/v1/topics/batch/dry-run?cluster_id=${clusterId}`, batchRequest),
  create: (clusterId: string, batchRequest: Record<string, unknown>) =>
    api.post(`/v1/topics/batch/apply?cluster_id=${clusterId}`, batchRequest),
  createFromYAML: (clusterId: string, yamlContent: string) =>
    api.post(`/v1/topics/batch/apply-yaml?cluster_id=${clusterId}`, { yaml_content: yamlContent }),
  updateMetadata: (
    clusterId: string,
    topicName: string,
    metadata: {
      owners: string[];
      doc: string | null;
      tags: string[];
      environment: string;
      slo: string | null;
      sla: string | null;
    }
  ) =>
    api.patch(`/v1/topics/${topicName}/metadata?cluster_id=${clusterId}`, metadata),
  delete: (clusterId: string, name: string) =>
    api.delete(`/v1/topics/${name}?cluster_id=${clusterId}`),
  bulkDelete: (clusterId: string, names: string[]) =>
    api.post(`/v1/topics/bulk-delete?cluster_id=${clusterId}`, names),
  getDetail: (clusterId: string, topicName: string) =>
    api.get(`/v1/topics/${topicName}/detail?cluster_id=${clusterId}`),
};

export const metricsAPI = {
  getTopicMetrics: (clusterId: string, topicName: string) =>
    api.get(`/metrics/topics/${topicName}?cluster_id=${clusterId}`),
  getTopicMetricsLive: (clusterId: string, topicName: string) =>
    api.get(`/metrics/topics/${topicName}/live?cluster_id=${clusterId}`),
  getAllTopicsMetrics: (clusterId: string) =>
    api.get(`/metrics/topics?cluster_id=${clusterId}`),
  getClusterMetrics: (clusterId: string) =>
    api.get(`/metrics/cluster?cluster_id=${clusterId}`),
  refreshMetrics: (clusterId: string) =>
    api.post(`/metrics/refresh?cluster_id=${clusterId}`),
  syncMetrics: (clusterId: string) =>
    api.post(`/metrics/sync?cluster_id=${clusterId}`),
};

export const schemasAPI = {
  list: () => api.get("/v1/schemas/artifacts"),
  sync: (registryId: string) =>
    api.post(`/v1/schemas/sync?registry_id=${registryId}`),
  upload: (registryId: string, formData: FormData) =>
    api.post(`/v1/schemas/upload?registry_id=${registryId}`, formData, {
      headers: { "Content-Type": "multipart/form-data" },
    }),
  delete: (registryId: string, subject: string) =>
    api.delete(`/v1/schemas/delete/${subject}?registry_id=${registryId}`),
  analyze: (registryId: string, subject: string) =>
    api.post(`/v1/schemas/delete/analyze?registry_id=${registryId}`, null, {
      params: { subject },
    }),
};

export const clustersAPI = {
  // Kafka Clusters (Brokers)
  listKafka: () => api.get("/v1/clusters/brokers"),
  getKafka: (clusterId: string) => api.get(`/v1/clusters/brokers/${clusterId}`),
  createKafka: (data: Record<string, string>) => api.post("/v1/clusters/brokers", data),
  updateKafka: (clusterId: string, data: Record<string, unknown>) => 
    api.put(`/v1/clusters/brokers/${clusterId}`, data),
  deleteKafka: (clusterId: string) => api.delete(`/v1/clusters/brokers/${clusterId}`),
  activateKafka: (clusterId: string) => api.patch(`/v1/clusters/brokers/${clusterId}/activate`),
  testKafka: (clusterId: string) =>
    api.post(`/v1/clusters/brokers/${clusterId}/test`),
  
  // Schema Registries
  listRegistries: () => api.get("/v1/clusters/schema-registries"),
  getRegistry: (registryId: string) => api.get(`/v1/clusters/schema-registries/${registryId}`),
  createRegistry: (data: Record<string, string>) => 
    api.post("/v1/clusters/schema-registries", data),
  updateRegistry: (registryId: string, data: Record<string, unknown>) => 
    api.put(`/v1/clusters/schema-registries/${registryId}`, data),
  deleteRegistry: (registryId: string) => 
    api.delete(`/v1/clusters/schema-registries/${registryId}`),
  activateRegistry: (registryId: string) => api.patch(`/v1/clusters/schema-registries/${registryId}/activate`),
  testRegistry: (registryId: string) =>
    api.post(`/v1/clusters/schema-registries/${registryId}/test`),
  
  // Object Storages
  listStorages: () => api.get("/v1/clusters/storages"),
  getStorage: (storageId: string) => api.get(`/v1/clusters/storages/${storageId}`),
  createStorage: (data: Record<string, string>) => 
    api.post("/v1/clusters/storages", data),
  updateStorage: (storageId: string, data: Record<string, unknown>) => 
    api.put(`/v1/clusters/storages/${storageId}`, data),
  deleteStorage: (storageId: string) => 
    api.delete(`/v1/clusters/storages/${storageId}`),
  activateStorage: (storageId: string) => api.patch(`/v1/clusters/storages/${storageId}/activate`),
  testStorage: (storageId: string) =>
    api.post(`/v1/clusters/storages/${storageId}/test`),
  
  // Kafka Connects
  listConnects: () => api.get("/v1/clusters/connects"),
  getConnect: (connectId: string) => api.get(`/v1/clusters/connects/${connectId}`),
  createConnect: (data: Record<string, string>) => 
    api.post("/v1/clusters/connects", data),
  updateConnect: (connectId: string, data: Record<string, unknown>) => 
    api.put(`/v1/clusters/connects/${connectId}`, data),
  deleteConnect: (connectId: string) => 
    api.delete(`/v1/clusters/connects/${connectId}`),
  activateConnect: (connectId: string) => api.patch(`/v1/clusters/connects/${connectId}/activate`),
  testConnect: (connectId: string) =>
    api.post(`/v1/clusters/connects/${connectId}/test`),
};

export const connectAPI = {
  list: (connectId: string, expand?: string) => {
    const params = expand ? `?expand=${expand}` : '';
    return api.get(`/v1/connect/${connectId}/connectors${params}`);
  },
  get: (connectId: string, name: string) =>
    api.get(`/v1/connect/${connectId}/connectors/${name}`),
  getConfig: (connectId: string, name: string) =>
    api.get(`/v1/connect/${connectId}/connectors/${name}/config`),
  getStatus: (connectId: string, name: string) =>
    api.get(`/v1/connect/${connectId}/connectors/${name}/status`),
  create: (connectId: string, config: Record<string, unknown>) =>
    api.post(`/v1/connect/${connectId}/connectors`, config),
  updateConfig: (connectId: string, name: string, config: Record<string, unknown>) =>
    api.put(`/v1/connect/${connectId}/connectors/${name}/config`, config),
  delete: (connectId: string, name: string) =>
    api.delete(`/v1/connect/${connectId}/connectors/${name}`),
  pause: (connectId: string, name: string) =>
    api.put(`/v1/connect/${connectId}/connectors/${name}/pause`, {}),
  resume: (connectId: string, name: string) =>
    api.put(`/v1/connect/${connectId}/connectors/${name}/resume`, {}),
  restart: (connectId: string, name: string) =>
    api.post(`/v1/connect/${connectId}/connectors/${name}/restart`),
  // Task operations
  getTasks: (connectId: string, name: string) =>
    api.get(`/v1/connect/${connectId}/connectors/${name}/tasks`),
  getTaskStatus: (connectId: string, name: string, taskId: number) =>
    api.get(`/v1/connect/${connectId}/connectors/${name}/tasks/${taskId}/status`),
  restartTask: (connectId: string, name: string, taskId: number) =>
    api.post(`/v1/connect/${connectId}/connectors/${name}/tasks/${taskId}/restart`),
  // Plugin operations
  getPlugins: (connectId: string) =>
    api.get(`/v1/connect/${connectId}/connector-plugins`),
  validateConfig: (connectId: string, pluginClass: string, config: Record<string, unknown>) =>
    api.put(`/v1/connect/${connectId}/connector-plugins/${pluginClass}/config/validate`, config),
  // Topic operations
  getTopics: (connectId: string, name: string) =>
    api.get(`/v1/connect/${connectId}/connectors/${name}/topics`),
  resetTopics: (connectId: string, name: string) =>
    api.put(`/v1/connect/${connectId}/connectors/${name}/topics/reset`, {}),
  // Metadata operations (거버넌스)
  getMetadata: (connectId: string, name: string) =>
    api.get(`/v1/connect/${connectId}/connectors/${name}/metadata`),
  updateMetadata: (connectId: string, name: string, metadata: Record<string, unknown>) =>
    api.patch(`/v1/connect/${connectId}/connectors/${name}/metadata`, metadata),
  deleteMetadata: (connectId: string, name: string) =>
    api.delete(`/v1/connect/${connectId}/connectors/${name}/metadata`),
  getMetadataByTeam: (connectId: string, team: string) =>
    api.get(`/v1/connect/${connectId}/metadata/by-team/${team}`),
};

export const policiesAPI = {
  list: (policyType?: string, status?: string) => {
    const params = new URLSearchParams();
    if (policyType) params.append("policy_type", policyType);
    if (status) params.append("status", status);
    return api.get(`/v1/policies?${params.toString()}`);
  },
  get: (policyId: string) => api.get(`/v1/policies/${policyId}`),
  getActive: (policyId: string) => api.get(`/v1/policies/${policyId}/active`),
  getVersions: (policyId: string) => api.get(`/v1/policies/${policyId}/versions`),
  create: (data: Record<string, unknown>) => api.post("/v1/policies", data),
  update: (policyId: string, data: Record<string, unknown>) =>
    api.put(`/v1/policies/${policyId}`, data),
  delete: (policyId: string, version?: number) => {
    const params = version !== undefined ? `?version=${version}` : '';
    return api.delete(`/v1/policies/${policyId}${params}`);
  },
  deleteAll: (policyId: string) => api.delete(`/v1/policies/${policyId}/all`),
  activate: (policyId: string, version?: number) =>
    api.post(`/v1/policies/${policyId}/activate`, version !== undefined ? { version } : {}),
  archive: (policyId: string) =>
    api.post(`/v1/policies/${policyId}/archive`),
  rollback: (policyId: string, targetVersion: number, createdBy: string = "system") =>
    api.post(`/v1/policies/${policyId}/rollback`, { target_version: targetVersion, created_by: createdBy }),
};

export const auditAPI = {
  recent: (limit = 20) => api.get(`/v1/audit/recent?limit=${limit}`),
  history: (params: Record<string, unknown>) => api.get("/v1/audit/history", { params }),
};

export const analysisAPI = {
  statistics: () => api.get("/v1/analysis/statistics"),
  correlations: () => api.get("/v1/analysis/correlations"),
  topicSchemas: (topicName: string) =>
    api.get(`/v1/analysis/correlations/topic/${topicName}`),
  schemaImpact: (subject: string) =>
    api.get(`/v1/analysis/impact/schema/${subject}`),
};

export const consumerAPI = {
  // Consumer Groups 목록
  listGroups: (clusterId: string) =>
    api.get(`/v1/consumers/groups?cluster_id=${clusterId}`),
  
  // Consumer Group 메트릭
  getMetrics: (clusterId: string, groupId: string) =>
    api.get(`/v1/consumers/groups/${groupId}/metrics?cluster_id=${clusterId}`),
  
  // Consumer Group 상세 요약
  getSummary: (clusterId: string, groupId: string) =>
    api.get(`/v1/consumers/groups/${groupId}/summary?cluster_id=${clusterId}`),
  
  // 멤버 목록
  getMembers: (clusterId: string, groupId: string) =>
    api.get(`/v1/consumers/groups/${groupId}/members?cluster_id=${clusterId}`),
  
  // 파티션 목록
  getPartitions: (clusterId: string, groupId: string) =>
    api.get(`/v1/consumers/groups/${groupId}/partitions?cluster_id=${clusterId}`),
  
  // 리밸런스 이벤트
  getRebalanceEvents: (clusterId: string, groupId: string, limit = 10) =>
    api.get(`/v1/consumers/groups/${groupId}/rebalance?cluster_id=${clusterId}&limit=${limit}`),
  
  // 정책 어드바이저
  getAdvice: (clusterId: string, groupId: string) =>
    api.get(`/v1/consumers/groups/${groupId}/advice?cluster_id=${clusterId}`),
  
  // 토픽별 컨슈머 매핑
  getTopicConsumers: (clusterId: string, topic: string) =>
    api.get(`/v1/topics/${topic}/consumers?cluster_id=${clusterId}`),
};
