import axios from "axios";
import type { AuditLog, KafkaCluster, SchemaRegistry } from "../types";

const api = axios.create({
  baseURL: "/api/",
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
    const response = await api.get("/v1");
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

export const schemasAPI = {
  list: () => api.get("/v1/schemas/artifacts"),
  sync: (registryId: string) =>
    api.post(`/v1/schemas/sync?registry_id=${registryId}`),
  upload: (registryId: string, formData: FormData) =>
    api.post(`/v1/schemas/upload?registry_id=${registryId}`, formData, {
      headers: { "Content-Type": "multipart/form-data" },
    }),
  delete: (registryId: string, subject: string, force: boolean = false) =>
    api.delete(`/v1/schemas/delete/${subject}?registry_id=${registryId}&force=${force}`),
  analyze: (registryId: string, subject: string) =>
    api.post(`/v1/schemas/delete/analyze?registry_id=${registryId}`, null, {
      params: { subject },
    }),
  dryRun: (registryId: string, data: Record<string, unknown>) =>
    api.post(`/v1/schemas/batch/dry-run?registry_id=${registryId}`, data),
  apply: (registryId: string, data: object) =>
    api.post(`/v1/schemas/batch/apply?registry_id=${registryId}`, data),
  planChange: (registryId: string, data: { subject: string; new_schema: string; compatibility: string }) =>
    api.post(`/v1/schemas/plan-change?registry_id=${registryId}`, data),
  planRollback: (registryId: string, data: { subject: string; version: number }) =>
    api.post(`/v1/schemas/rollback/plan?registry_id=${registryId}`, data),
};

export const clustersAPI = {
  // Kafka Clusters (Brokers)
  listKafka: () => api.get<KafkaCluster[]>("/v1/clusters/brokers"),
  getKafka: (clusterId: string) => api.get<KafkaCluster>(`/v1/clusters/brokers/${clusterId}`),
  createKafka: (data: Record<string, string>) => api.post("/v1/clusters/brokers", data),
  updateKafka: (clusterId: string, data: Record<string, unknown>) =>
    api.put(`/v1/clusters/brokers/${clusterId}`, data),
  deleteKafka: (clusterId: string) => api.delete(`/v1/clusters/brokers/${clusterId}`),
  activateKafka: (clusterId: string) => api.patch(`/v1/clusters/brokers/${clusterId}/activate`),
  testKafka: (clusterId: string) =>
    api.post(`/v1/clusters/brokers/${clusterId}/test`),

  // Schema Registries
  listRegistries: () => api.get<SchemaRegistry[]>("/v1/clusters/schema-registries"),
  getRegistry: (registryId: string) => api.get<SchemaRegistry>(`/v1/clusters/schema-registries/${registryId}`),
  createRegistry: (data: Record<string, string>) =>
    api.post("/v1/clusters/schema-registries", data),
  updateRegistry: (registryId: string, data: Record<string, unknown>) =>
    api.put(`/v1/clusters/schema-registries/${registryId}`, data),
  deleteRegistry: (registryId: string) =>
    api.delete(`/v1/clusters/schema-registries/${registryId}`),
  activateRegistry: (registryId: string) => api.patch(`/v1/clusters/schema-registries/${registryId}/activate`),
  testRegistry: (registryId: string) =>
    api.post(`/v1/clusters/schema-registries/${registryId}/test`),
};

export const auditAPI = {
  recent: (limit = 20) => api.get<AuditLog[]>(`/v1/audit/recent?limit=${limit}`),
  history: (params: Record<string, unknown>) => api.get("/v1/audit/history", { params }),
};
