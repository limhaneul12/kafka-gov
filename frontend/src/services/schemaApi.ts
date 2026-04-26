import axios from 'axios';
import {
    type ApprovalRequestResponse,
    type AuditActivityResponse,
    type DashboardResponse,
    type SchemaDriftResponse,
    type SchemaHistoryResponse,
    type SchemaSearchParams,
    type SchemaSearchResponse,
} from '../types/schema';
import type { SchemaPolicyStatus } from '../types/schemaPolicy';
import type { SchemaPolicyFormInput, SchemaPolicyRecord } from '../types/schemaPolicy';

const BASE_URL = '/api/v1/schemas';

const schemaApi = {
    getDashboardStats: async (registryId: string): Promise<DashboardResponse> => {
        const response = await axios.get<DashboardResponse>(`${BASE_URL}/governance/dashboard`, {
            params: { registry_id: registryId },
        });
        return response.data;
    },

    getDetail: async (subject: string, registryId: string): Promise<unknown> => {
        const response = await axios.get(`${BASE_URL}/detail/${encodeURIComponent(subject)}`, {
            params: { registry_id: registryId },
        });
        return response.data;
    },

    searchSchemas: async (params: SchemaSearchParams): Promise<SchemaSearchResponse> => {
        const response = await axios.get<SchemaSearchResponse>(`${BASE_URL}/search`, {
            params,
        });
        return response.data;
    },

    getHistory: async (subject: string, registryId: string = 'default'): Promise<SchemaHistoryResponse> => {
        const response = await axios.get<SchemaHistoryResponse>(`${BASE_URL}/history/${encodeURIComponent(subject)}`, {
            params: { registry_id: registryId },
        });
        return response.data;
    },

    getDrift: async (subject: string, registryId: string = 'default'): Promise<SchemaDriftResponse> => {
        const response = await axios.get<SchemaDriftResponse>(`${BASE_URL}/drift/${encodeURIComponent(subject)}`, {
            params: { registry_id: registryId },
        });
        return response.data;
    },

    listApprovalRequests: async (params?: {
        status?: string;
        resource_type?: string;
        requested_by?: string;
        limit?: number;
    }): Promise<ApprovalRequestResponse[]> => {
        const response = await axios.get<ApprovalRequestResponse[]>(`/api/v1/approval-requests`, { params });
        return response.data;
    },

    getApprovalRequest: async (requestId: string): Promise<ApprovalRequestResponse> => {
        const response = await axios.get<ApprovalRequestResponse>(`/api/v1/approval-requests/${requestId}`);
        return response.data;
    },

    approveApprovalRequest: async (
        requestId: string,
        payload: { approver: string; decision_reason?: string },
    ): Promise<ApprovalRequestResponse> => {
        const response = await axios.post<ApprovalRequestResponse>(
            `/api/v1/approval-requests/${requestId}/approve`,
            payload,
        );
        return response.data;
    },

    rejectApprovalRequest: async (
        requestId: string,
        payload: { approver: string; decision_reason?: string },
    ): Promise<ApprovalRequestResponse> => {
        const response = await axios.post<ApprovalRequestResponse>(
            `/api/v1/approval-requests/${requestId}/reject`,
            payload,
        );
        return response.data;
    },

    getRecentAuditActivities: async (limit = 20): Promise<AuditActivityResponse[]> => {
        const response = await axios.get<AuditActivityResponse[]>(`/api/v1/audit/recent`, {
            params: { limit },
        });
        return response.data;
    },

    getAuditHistory: async (params?: {
        from_date?: string;
        to_date?: string;
        activity_type?: string;
        action?: string;
        actor?: string;
        limit?: number;
    }): Promise<AuditActivityResponse[]> => {
        const response = await axios.get<AuditActivityResponse[]>(`/api/v1/audit/history`, {
            params,
        });
        return response.data;
    },

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
