import axios from "axios";
import type { SchemaRegistry } from "../types";

const api = axios.create({
  baseURL: "/api/",
  headers: {
    "Content-Type": "application/json",
  },
});

api.interceptors.request.use(
  (config) => config,
  (error) => Promise.reject(error),
);

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response) {
      console.error("API Error Response:", {
        status: error.response.status,
        data: error.response.data,
        url: error.config?.url,
      });
    } else if (error.request) {
      console.error("API No Response:", {
        message: error.message,
        url: error.config?.url,
        baseURL: error.config?.baseURL,
      });
    } else {
      console.error("API Request Setup Error:", error.message);
    }
    return Promise.reject(error);
  },
);

export const testAPIConnection = async () => {
  try {
    const response = await api.get("/v1");
    return { success: true, data: response.data };
  } catch (error: unknown) {
    const err = error as {
      message?: string;
      response?: { data?: unknown };
      config?: { url?: string; baseURL?: string };
      request?: unknown;
    };
    console.error("❌ API Connection Failed:", err.message);
    return {
      success: false,
      error: err.response?.data || err.message,
      details: {
        url: err.config?.url,
        baseURL: err.config?.baseURL,
        hasResponse: !!err.response,
        hasRequest: !!err.request,
      },
    };
  }
};

export default api;

export const schemasAPI = {
  list: () => api.get("/v1/schemas/artifacts"),
  sync: (registryId: string) => api.post(`/v1/schemas/sync?registry_id=${registryId}`),
  upload: (registryId: string, formData: FormData) =>
    api.post(`/v1/schemas/upload?registry_id=${registryId}`, formData, {
      headers: { "Content-Type": "multipart/form-data" },
    }),
  delete: (registryId: string, subject: string, force = false) =>
    api.delete(`/v1/schemas/delete/${subject}?registry_id=${registryId}&force=${force}`),
  analyze: (registryId: string, subject: string) =>
    api.post(`/v1/schemas/delete/analyze?registry_id=${registryId}`, null, {
      params: { subject },
    }),
  dryRun: (registryId: string, data: Record<string, unknown>) =>
    api.post(`/v1/schemas/batch/dry-run?registry_id=${registryId}`, data),
  apply: (registryId: string, data: object) =>
    api.post(`/v1/schemas/batch/apply?registry_id=${registryId}`, data),
  planChange: (
    registryId: string,
    data: { subject: string; new_schema: string; compatibility: string },
  ) => api.post(`/v1/schemas/plan-change?registry_id=${registryId}`, data),
  planRollback: (registryId: string, data: { subject: string; version: number }) =>
    api.post(`/v1/schemas/rollback/plan?registry_id=${registryId}`, data),
};

export const registryAPI = {
  list: () => api.get<SchemaRegistry[]>("/v1/schema-registries"),
  get: (registryId: string) => api.get<SchemaRegistry>(`/v1/schema-registries/${registryId}`),
  create: (data: Record<string, string>) => api.post("/v1/schema-registries", data),
  update: (registryId: string, data: Record<string, unknown>) =>
    api.put(`/v1/schema-registries/${registryId}`, data),
  delete: (registryId: string) => api.delete(`/v1/schema-registries/${registryId}`),
  activate: (registryId: string) => api.patch(`/v1/schema-registries/${registryId}/activate`),
  test: (registryId: string) => api.post(`/v1/schema-registries/${registryId}/test`),
};
