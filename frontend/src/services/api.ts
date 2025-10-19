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
export const testConnection = async () => {
  try {
    const response = await api.get("/");
    console.log("✅ API Connection OK:", response.data);
    return { success: true, data: response.data };
  } catch (error: any) {
    console.error("❌ API Connection Failed:", error.message);
    return { 
      success: false, 
      error: error.response?.data || error.message,
      details: {
        url: error.config?.url,
        baseURL: error.config?.baseURL,
        hasResponse: !!error.response,
        hasRequest: !!error.request,
      }
    };
  }
};

export default api;

// API 엔드포인트 함수들
export const topicsAPI = {
  list: (clusterId: string) => api.get(`/v1/topics?cluster_id=${clusterId}`),
  create: (clusterId: string, data: any) =>
    api.post(`/v1/topics/batch/apply?cluster_id=${clusterId}`, data),
  delete: (clusterId: string, name: string) =>
    api.delete(`/v1/topics/${name}?cluster_id=${clusterId}`),
  bulkDelete: (clusterId: string, names: string[]) =>
    api.post(`/v1/topics/bulk-delete?cluster_id=${clusterId}`, names),
};

export const schemasAPI = {
  list: () => api.get("/v1/schemas/artifacts"),
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
  listKafka: () => api.get("/v1/clusters/kafka"),
  createKafka: (data: any) => api.post("/v1/clusters/kafka", data),
  testKafka: (clusterId: string) =>
    api.post(`/v1/clusters/kafka/${clusterId}/test`),
  listRegistries: () => api.get("/v1/clusters/schema-registries"),
  listStorages: () => api.get("/v1/clusters/storages"),
  listConnects: () => api.get("/v1/clusters/connects"),
};

export const connectAPI = {
  list: (connectId: string) =>
    api.get(`/v1/connect/${connectId}/connectors`),
  get: (connectId: string, name: string) =>
    api.get(`/v1/connect/${connectId}/connectors/${name}`),
  create: (connectId: string, config: any) =>
    api.post(`/v1/connect/${connectId}/connectors`, config),
  delete: (connectId: string, name: string) =>
    api.delete(`/v1/connect/${connectId}/connectors/${name}`),
  pause: (connectId: string, name: string) =>
    api.post(`/v1/connect/${connectId}/connectors/${name}/pause`),
  resume: (connectId: string, name: string) =>
    api.post(`/v1/connect/${connectId}/connectors/${name}/resume`),
  restart: (connectId: string, name: string) =>
    api.post(`/v1/connect/${connectId}/connectors/${name}/restart`),
};

export const policiesAPI = {
  list: () => api.get("/v1/policies"),
  get: (policyId: string) => api.get(`/v1/policies/${policyId}`),
  create: (data: any) => api.post("/v1/policies", data),
  update: (policyId: string, data: any) =>
    api.put(`/v1/policies/${policyId}`, data),
  delete: (policyId: string) => api.delete(`/v1/policies/${policyId}`),
  activate: (policyId: string, version: number) =>
    api.post(`/v1/policies/${policyId}/activate`, { version }),
};

export const auditAPI = {
  recent: (limit = 20) => api.get(`/v1/audit/recent?limit=${limit}`),
  history: (params: any) => api.get("/v1/audit/history", { params }),
};

export const analysisAPI = {
  statistics: () => api.get("/v1/analysis/statistics"),
  correlations: () => api.get("/v1/analysis/correlations"),
  topicSchemas: (topicName: string) =>
    api.get(`/v1/analysis/correlations/topic/${topicName}`),
  schemaImpact: (subject: string) =>
    api.get(`/v1/analysis/impact/schema/${subject}`),
};
