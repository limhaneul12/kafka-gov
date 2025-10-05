/**
 */

class ApiClient {
    constructor() {
        this.baseURL = '/api/v1';
        this.timeout = 30000;
        this.defaultHeaders = {
            'Content-Type': 'application/json',
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
    async getTopics() {
        return this.get('/topics');
    }

    /**
     * 토픽 배치 YAML 업로드
     */
    async topicBatchUpload(file) {
        const formData = new FormData();
        formData.append('file', file);
        
        return this.request('/topics/batch/upload', {
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
    async topicBatchApply(batch) {
        return this.post('/topics/batch/apply', batch);
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
        return this.post('/topics/bulk-delete', topicNames);
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
        return this.get('/analysis/statistics/schemas');
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
    async schemaBatchDryRun(batch) {
        return this.post('/schemas/batch/dry-run', batch);
    }

    /**
     * 스키마 배치 적용
     */
    async schemaBatchApply(batch) {
        return this.post('/schemas/batch/apply', batch);
    }

    /**
     * 스키마 파일 업로드
     */
    async uploadSchemaFiles({ env, changeId, owner, files }) {
        const formData = new FormData();
        formData.append('env', env);
        formData.append('change_id', changeId);
        formData.append('owner', owner);
        for (const file of files) {
            formData.append('files', file);
        }

        return this.request('/schemas/upload', {
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
    async syncSchemas() {
        return this.post('/schemas/sync');
    }

    // =================
    // Audit API
    // =================

    /**
     * 최근 활동 조회
     */
    async getRecentActivities(limit = 20) {
        return this.get(`/audit/recent?limit=${limit}`);
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
        
        const queryString = params.toString();
        return this.get(`/audit/history${queryString ? '?' + queryString : ''}`);
    }

    // =================
    // Cluster API
    // =================

    /**
     * Kafka 클러스터 상태 조회
     */
    async getClusterStatus() {
        return this.get('/cluster/status');
    }
}

// 전역 API 클라이언트 인스턴스
const api = new ApiClient();
window.api = api;
