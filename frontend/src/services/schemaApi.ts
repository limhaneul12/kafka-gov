import axios from 'axios';
import {
    type DashboardResponse,
    type ImpactGraphResponse,
    type SchemaHistoryResponse,
    type SchemaSearchParams,
    type SchemaSearchResponse,
} from '../types/schema';

// Vite Proxy 설정으로 가정 (/api -> Backend)
const BASE_URL = '/api/v1/schemas';

const schemaApi = {
    // 거버넌스 대시보드
    getDashboardStats: async (registryId: string): Promise<DashboardResponse> => {
        const response = await axios.get<DashboardResponse>(`${BASE_URL}/governance/dashboard`, {
            params: { registry_id: registryId },
        });
        return response.data;
    },

    // 스키마 단건 상세 조회
    getDetail: async (subject: string, registryId: string): Promise<any> => {
        const response = await axios.get(`${BASE_URL}/detail/${encodeURIComponent(subject)}`, {
            params: { registry_id: registryId },
        });
        return response.data;
    },

    // 스키마 검색
    searchSchemas: async (params: SchemaSearchParams): Promise<SchemaSearchResponse> => {
        const response = await axios.get<SchemaSearchResponse>(`${BASE_URL}/search`, {
            params,
        });
        return response.data;
    },

    // 스키마 이력 조회
    getHistory: async (subject: string, registryId: string = 'default'): Promise<SchemaHistoryResponse> => {
        const response = await axios.get<SchemaHistoryResponse>(`${BASE_URL}/history/${encodeURIComponent(subject)}`, {
            params: { registry_id: registryId },
        });
        return response.data;
    },

    // 스키마 영향도 그래프 조회
    getImpactGraph: async (subject: string, registryId: string = 'default'): Promise<ImpactGraphResponse> => {
        const response = await axios.get<ImpactGraphResponse>(`${BASE_URL}/impact/${encodeURIComponent(subject)}`, {
            params: { registry_id: registryId },
        });
        return response.data;
    },

    // --- 정책 관리 (Policy Management) ---
    listPolicies: async (params?: { env?: string; policy_type?: string }): Promise<any[]> => {
        const response = await axios.get(`/api/schemas/policies`, { params });
        return response.data;
    },

    createPolicy: async (data: any): Promise<any> => {
        const response = await axios.post(`/api/schemas/policies`, data);
        return response.data;
    },

    getPolicyDetail: async (policyId: string, version?: number): Promise<any> => {
        const response = await axios.get(`/api/schemas/policies/${policyId}`, {
            params: { version }
        });
        return response.data;
    },

    getPolicyHistory: async (policyId: string): Promise<any[]> => {
        const response = await axios.get(`/api/schemas/policies/${policyId}/history`);
        return response.data;
    },

    updatePolicyStatus: async (policyId: string, version: number, status: string): Promise<void> => {
        await axios.patch(`/api/schemas/policies/status`, {
            policy_id: policyId,
            version,
            status,
        });
    },
};

export default schemaApi;
