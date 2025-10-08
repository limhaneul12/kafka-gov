/**
 */

class ApiClient {
    constructor() {
        this.baseURL = '/api';  // 수정: /api/v1 → /api
        this.timeout = 30000;
        this.defaultHeaders = {
            'Content-Type': 'application/json',
        };
        
        // 현재 선택된 클러스터/레지스트리/스토리지/커넥트 (localStorage에서 로드)
        this.currentClusterId = localStorage.getItem('currentClusterId') || 'default';
        this.currentRegistryId = localStorage.getItem('currentRegistryId') || 'default';
        this.currentStorageId = localStorage.getItem('currentStorageId') || null;
        this.currentConnectId = localStorage.getItem('currentConnectId') || null;
    }
    
    /**
     * 클러스터 ID 설정
     */
    setClusterId(clusterId) {
        this.currentClusterId = clusterId;
        localStorage.setItem('currentClusterId', clusterId);
    }
    
    /**
     * 레지스트리 ID 설정
     */
    setRegistryId(registryId) {
        this.currentRegistryId = registryId;
        localStorage.setItem('currentRegistryId', registryId);
    }
    
    /**
     * 스토리지 ID 설정
     */
    setStorageId(storageId) {
        this.currentStorageId = storageId;
        localStorage.setItem('currentStorageId', storageId || '');
    }
    
    /**
     * Kafka Connect ID 설정
     */
    setConnectId(connectId) {
        this.currentConnectId = connectId;
        localStorage.setItem('currentConnectId', connectId || '');
    }
    
    /**
     * 현재 설정 조회
     */
    getCurrentSettings() {
        return {
            clusterId: this.currentClusterId,
            registryId: this.currentRegistryId,
            storageId: this.currentStorageId,
            connectId: this.currentConnectId
        };
    }

    /**
     * HTTP 요청 헬퍼
     */
    async request(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        
        // FormData인 경우 Content-Type을 설정하지 않음 (브라우저가 자동 설정)
        const isFormData = options.body instanceof FormData;
        
        const config = {
            headers: isFormData ? {
                ...options.headers,
            } : {
                'Content-Type': 'application/json',
                ...options.headers,
            },
            ...options,
        };

        try {
            const response = await fetch(url, config);
            
            if (!response.ok) {
                const error = await response.json().catch(() => ({}));
                // 에러 메시지를 더 명확하게 처리
                let errorMessage = error.detail || `HTTP ${response.status}`;
                
                // detail이 배열인 경우 (FastAPI validation error)
                if (Array.isArray(error.detail)) {
                    errorMessage = error.detail.map(err => {
                        const loc = err.loc ? err.loc.join(' > ') : '';
                        return `${loc}: ${err.msg}`;
                    }).join('\n');
                }
                
                throw new Error(errorMessage);
            }

            // 응답이 비어있으면 null 반환
            const text = await response.text();
            return text ? JSON.parse(text) : null;
        } catch (error) {
            console.error(`API 요청 실패: ${endpoint}`, error);
            throw error;
        }
    }

    /**
     * GET 요청
     */
    async get(endpoint, params = {}) {
        const searchParams = new URLSearchParams(params);
        const url = searchParams.toString() ? `${endpoint}?${searchParams}` : endpoint;
        return this.request(url, { method: 'GET' });
    }

    /**
     * POST 요청
     */
    async post(endpoint, data = null) {
        return this.request(endpoint, {
            method: 'POST',
            body: data ? JSON.stringify(data) : null,
        });
    }

    /**
     * PUT 요청
     */
    async put(endpoint, data = null) {
        return this.request(endpoint, {
            method: 'PUT',
            body: data ? JSON.stringify(data) : null,
        });
    }

    /**
     * DELETE 요청
     */
    async delete(endpoint) {
        return this.request(endpoint, { method: 'DELETE' });
    }

    /**
     * 파일 업로드
     */
    async uploadFiles(endpoint, files) {
        const formData = new FormData();
        for (const file of files) {
            formData.append('files', file);
        }

        return this.request(endpoint, {
            method: 'POST',
            headers: {
                // Content-Type을 설정하지 않음 (브라우저가 자동으로 multipart/form-data 설정)
            },
            body: formData,
        });
    }
    // =================
    // Topic API
    // =================

    /**
     * 토픽 목록 조회
     */
    async getTopics(clusterId = null) {
        const id = clusterId || this.currentClusterId;
        return this.get('/v1/topics', { cluster_id: id });
    }

    /**
     * 토픽 배치 YAML 업로드
     */
    async topicBatchUpload(file, clusterId = null) {
        const id = clusterId || this.currentClusterId;
        const formData = new FormData();
        formData.append('file', file);
        
        return this.request(`/v1/topics/batch/upload?cluster_id=${id}`, {
            method: 'POST',
            body: formData,
        });
    }

    /**
     * 토픽 배치 Dry-run
     */
    async topicBatchDryRun(batch) {
        return this.post('/topics/batch/dry-run', batch);
    }

    /**
     * 토픽 배치 적용
     */
    async topicBatchApply(batch, clusterId = null) {
        const id = clusterId || this.currentClusterId;
        return this.post(`/v1/topics/batch/apply?cluster_id=${id}`, batch);
    }

    /**
     * 토픽 삭제
     */
    async deleteTopic(topicName) {
        return this.delete(`/topics/${encodeURIComponent(topicName)}`);
    }

    /**
     * 토픽 일괄 삭제
     */
    async bulkDeleteTopics(topicNames) {
        const id = this.currentClusterId;
        return this.post(`/v1/topics/bulk-delete?cluster_id=${id}`, topicNames);
    }


    // =================
    // Analysis API
    // =================

    /**
     * 토픽-스키마 상관관계 전체 조회
     */
    async getAllCorrelations(params = {}) {
        return this.get('/analysis/correlations', params);
    }

    /**
     * 토픽 개수 조회
     */
    async getTopicCount() {
        return this.get('/analysis/statistics/topics');
    }

    /**
     * 스키마 개수 조회
     */
    async getSchemaCount() {
        return this.get('/v1/analysis/statistics/schemas');
    }

    /**
     * 전체 통계 조회
     */
    async getStatistics() {
        return this.get('/analysis/statistics');
    }



    // =================
    // Schema API
    // =================
    /**
     * 스키마 배치 Dry Run
     */
    async schemaBatchDryRun(batch, registryId = null) {
        const id = registryId || this.currentRegistryId;
        return this.post(`/v1/schemas/batch/dry-run?registry_id=${id}`, batch);
    }

    /**
     * 스키마 배치 적용
     */
    async schemaBatchApply(batch, registryId = null, storageId = null) {
        const regId = registryId || this.currentRegistryId;
        const stgId = storageId || this.currentStorageId;
        let url = `/v1/schemas/batch/apply?registry_id=${regId}`;
        if (stgId) {
            url += `&storage_id=${stgId}`;
        }
        return this.post(url, batch);
    }

    /**
     * 스키마 파일 업로드
     */
    async uploadSchemaFiles({ env, changeId, owner, files, compatibilityMode, registryId = null, storageId = null }) {
        const regId = registryId || this.currentRegistryId;
        const stgId = storageId || this.currentStorageId;
        
        const formData = new FormData();
        formData.append('env', env);
        formData.append('change_id', changeId);
        formData.append('owner', owner);
        if (compatibilityMode) {
            formData.append('compatibility_mode', compatibilityMode);
        }
        for (const file of files) {
            formData.append('files', file);
        }

        let url = `/v1/schemas/upload?registry_id=${regId}`;
        if (stgId) {
            url += `&storage_id=${stgId}`;
        }

        return this.request(url, {
            method: 'POST',
            body: formData,
        });
    }

    /**
     * 스키마 계획 조회
     */
    async getSchemaPlan(changeId) {
        return this.get(`/schemas/plan/${encodeURIComponent(changeId)}`);
    }

    /**
     * 스키마 삭제 영향도 분석
     */
    async analyzeSchemaDelete(subject, strategy = 'TopicNameStrategy') {
        return this.post(`/schemas/delete/analyze?subject=${encodeURIComponent(subject)}&strategy=${strategy}`, null);
    }

    /**
     * 스키마 삭제
     */
    async deleteSchema(subject, strategy = 'TopicNameStrategy', force = false) {
        return this.delete(`/schemas/delete/${encodeURIComponent(subject)}?strategy=${strategy}&force=${force}`);
    }

    /**
     * 스키마 아티팩트 목록 조회
     */
    async getSchemaArtifacts() {
        return this.get('/schemas/artifacts');
    }

    /**
     * 스키마 동기화 (Schema Registry → DB)
     */
    async syncSchemas(registryId = null) {
        const id = registryId || this.currentRegistryId;
        return this.post(`/v1/schemas/sync?registry_id=${id}`);
    }

    // =================
    // Audit API
    // =================

    /**
     * 최근 활동 조회
     */
    async getRecentActivities(limit = 20) {
        return this.get(`/v1/audit/recent?limit=${limit}`);
    }

    /**
     * 활동 히스토리 조회 (필터링 지원)
     */
    async getActivityHistory(filters = {}) {
        const params = new URLSearchParams();
        
        if (filters.from_date) params.append('from_date', filters.from_date);
        if (filters.to_date) params.append('to_date', filters.to_date);
        if (filters.activity_type) params.append('activity_type', filters.activity_type);
        if (filters.action) params.append('action', filters.action);
        if (filters.actor) params.append('actor', filters.actor);
        if (filters.limit) params.append('limit', filters.limit);
        
        const query = params.toString();
        const url = query ? `/v1/audit/history?${query}` : '/v1/audit/history';
        return this.get(url);
    }

    /**
     * Kafka 클러스터 상태 조회
     */
    async getClusterStatus(clusterId = null) {
        const id = clusterId || this.currentClusterId;
        return this.get('/v1/cluster/status', { cluster_id: id });
    }

    // =================
    // Cluster API
    // =================

    /**
     * Kafka 클러스터 목록 조회
     */
    async getKafkaClusters(activeOnly = true) {
        return this.get('/v1/clusters/kafka', { active_only: activeOnly });
    }

    /**
     * Kafka 클러스터 생성
     */
    async createKafkaCluster(data) {
        return this.post('/v1/clusters/kafka', data);
    }

    /**
     * Kafka 클러스터 조회
     */
    async getKafkaCluster(clusterId) {
        return this.get(`/v1/clusters/kafka/${clusterId}`);
    }

    /**
     * Kafka 클러스터 수정
     */
    async updateKafkaCluster(clusterId, data) {
        return this.put(`/v1/clusters/kafka/${clusterId}`, data);
    }

    /**
     * Kafka 클러스터 삭제
     */
    async deleteKafkaCluster(clusterId) {
        return this.delete(`/v1/clusters/kafka/${clusterId}`);
    }

    /**
     * Kafka 연결 테스트
     */
    async testKafkaConnection(clusterId) {
        return this.post(`/v1/clusters/kafka/${clusterId}/test`);
    }

    /**
     * Schema Registry 목록 조회
     */
    async getSchemaRegistries(activeOnly = true) {
        return this.get('/v1/clusters/schema-registries', { active_only: activeOnly });
    }

    /**
     * Schema Registry 생성
     */
    async createSchemaRegistry(data) {
        return this.post('/v1/clusters/schema-registries', data);
    }

    /**
     * Schema Registry 연결 테스트
     */
    async testSchemaRegistryConnection(registryId) {
        return this.post(`/v1/clusters/schema-registries/${registryId}/test`);
    }

    /**
     * Object Storage 목록 조회
     */
    async getObjectStorages(activeOnly = true) {
        return this.get('/v1/clusters/storages', { active_only: activeOnly });
    }

    /**
     * Object Storage 생성
     */
    async createObjectStorage(data) {
        return this.post('/v1/clusters/storages', data);
    }

    /**
     * Object Storage 연결 테스트
     */
    async testObjectStorageConnection(storageId) {
        return this.post(`/v1/clusters/storages/${storageId}/test`);
    }

    /**
     * Kafka Connect 목록 조회
     */
    async getKafkaConnects(clusterId = null) {
        const params = {};
        if (clusterId) {
            params.cluster_id = clusterId;
        }
        return this.get('/v1/clusters/connects', params);
    }

    /**
     * Kafka Connect 생성
     */
    async createKafkaConnect(data) {
        return this.post('/v1/clusters/connects', data);
    }

    /**
     * Kafka Connect 조회
     */
    async getKafkaConnect(connectId) {
        return this.get(`/v1/clusters/connects/${connectId}`);
    }

    /**
     * Kafka Connect 삭제
     */
    async deleteKafkaConnect(connectId) {
        return this.delete(`/v1/clusters/connects/${connectId}`);
    }

    /**
     * Kafka Connect 연결 테스트
     */
    async testKafkaConnectConnection(connectId) {
        return this.post(`/v1/clusters/connects/${connectId}/test`);
    }

    // =================
    // Kafka Connect Connector API
    // =================

    /**
     * 커넥터 목록 조회
     */
    async getConnectors(connectId) {
        return this.get(`/v1/connect/${connectId}/connectors`);
    }

    /**
     * 커넥터 생성
     */
    async createConnector(connectId, config) {
        return this.post(`/v1/connect/${connectId}/connectors`, config);
    }

    /**
     * 커넥터 상세 조회
     */
    async getConnectorDetails(connectId, connectorName) {
        return this.get(`/v1/connect/${connectId}/connectors/${connectorName}`);
    }

    /**
     * 커넥터 상태 조회
     */
    async getConnectorStatus(connectId, connectorName) {
        return this.get(`/v1/connect/${connectId}/connectors/${connectorName}/status`);
    }

    /**
     * 커넥터 일시정지
     */
    async pauseConnector(connectId, connectorName) {
        return this.put(`/v1/connect/${connectId}/connectors/${connectorName}/pause`);
    }

    /**
     * 커넥터 재개
     */
    async resumeConnector(connectId, connectorName) {
        return this.put(`/v1/connect/${connectId}/connectors/${connectorName}/resume`);
    }

    /**
     * 커넥터 재시작
     */
    async restartConnector(connectId, connectorName) {
        return this.post(`/v1/connect/${connectId}/connectors/${connectorName}/restart`);
    }

    /**
     * 커넥터 삭제
     */
    async deleteConnector(connectId, connectorName) {
        return this.delete(`/v1/connect/${connectId}/connectors/${connectorName}`);
    }

    /**
     * Schema Registry 삭제
     */
    async deleteSchemaRegistry(registryId) {
        return this.delete(`/v1/clusters/schema-registries/${registryId}`);
    }

    /**
     * Object Storage 삭제
     */
    async deleteObjectStorage(storageId) {
        return this.delete(`/v1/clusters/storages/${storageId}`);
    }
}

// 전역 인스턴스 생성
const api = new ApiClient();
window.api = api;
