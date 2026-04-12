import axios from 'axios';
import {
    type DashboardResponse,
    type KnownTopicNamesResponse,
    type SchemaHistoryResponse,
    type SchemaSearchParams,
    type SchemaSearchResponse,
} from '../types/schema';
import type { SchemaPolicyStatus } from '../types/schemaPolicy';
import type { SchemaPolicyFormInput, SchemaPolicyRecord } from '../types/schemaPolicy';

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
    getDetail: async (subject: string, registryId: string): Promise<unknown> => {
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

    getKnownTopicNames: async (subject: string, registryId: string = 'default'): Promise<KnownTopicNamesResponse> => {
        const response = await axios.get<KnownTopicNamesResponse>(`${BASE_URL}/known-topics/${encodeURIComponent(subject)}`, {
            params: { registry_id: registryId },
        });
        return response.data;
    },

    // --- 정책 관리 (Policy Management) ---
    listPolicies: async (params?: { env?: string; policy_type?: string }): Promise<SchemaPolicyRecord[]> => {
        const response = await axios.get<SchemaPolicyRecord[]>(`/api/v1/schemas/policies`, { params });
        return response.data;
    },

    createPolicy: async (data: SchemaPolicyFormInput): Promise<SchemaPolicyRecord> => {
        const response = await axios.post<SchemaPolicyRecord>(`/api/v1/schemas/policies`, data);
        return response.data;
    },

    getPolicyDetail: async (policyId: string, version?: number): Promise<SchemaPolicyRecord> => {
        const response = await axios.get<SchemaPolicyRecord>(`/api/v1/schemas/policies/${policyId}`, {
            params: { version }
        });
        return response.data;
    },

    getPolicyHistory: async (policyId: string): Promise<SchemaPolicyRecord[]> => {
        const response = await axios.get<SchemaPolicyRecord[]>(`/api/v1/schemas/policies/${policyId}/history`);
        return response.data;
    },

    updatePolicyStatus: async (policyId: string, version: number, status: SchemaPolicyStatus): Promise<void> => {
        await axios.patch(`/api/v1/schemas/policies/status`, {
            policy_id: policyId,
            version,
            status,
        });
    },

    deletePolicy: async (policyId: string, version?: number): Promise<void> => {
        await axios.delete(`/api/v1/schemas/policies/${policyId}`, {
            params: { version }
        });
    },
};

export default schemaApi;
