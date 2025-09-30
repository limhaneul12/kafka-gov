/**
 */

class ApiClient {
    constructor() {
        this.baseURL = '/api';
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
        const config = {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers,
            },
            ...options,
        };


        try {
            const response = await fetch(url, config);
            
            if (!response.ok) {
                const error = await response.json().catch(() => ({}));
                throw new Error(error.detail || `HTTP ${response.status}`);
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
     * 토픽 상세 조회
     */
    async getTopicDetail(topicName) {
        return this.get(`/topics/${encodeURIComponent(topicName)}`);
    }

    /**
     * 토픽 계획 조회
     */
    async getTopicPlan(changeId) {
        return this.get(`/topics/plans/${encodeURIComponent(changeId)}`);
    }

    /**
     * 토픽 헬스 체크
     */
    async topicHealthCheck() {
        return this.get('/topics/health');
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
    async uploadSchemaFiles(files) {
        return this.uploadFiles('/schemas/upload', files);
    }

    /**
     * 스키마 계획 조회
     */
    async getSchemaPlan(changeId) {
        return this.get(`/schemas/plan/${encodeURIComponent(changeId)}`);
    }

    /**
     * 스키마 헬스 체크
     */
    async schemaHealthCheck() {
        return this.get('/schemas/health');
    }

    // =================
    // Policy API
    // =================

    /**
     * 정책 평가
     */
    async evaluatePolicy(request) {
        return this.post('/policies/evaluate', request);
    }

    /**
     * 검증 요약 조회
     */
    async getValidationSummary(environment, resourceType) {
        return this.get(`/policies/validation-summary/${environment}/${resourceType}`);
    }

    /**
     * 정책 목록 조회
     */
    async getPolicies() {
        return this.get('/policies/');
    }

    /**
     * 특정 정책 집합 조회
     */
    async getPolicySet(environment, resourceType) {
        return this.get(`/policies/${environment}/${resourceType}`);
    }

    /**
     * 기본 정책 초기화
     */
    async initializePolicies() {
        return this.post('/policies/initialize');
    }


    // =================
    // 헬스 체크
    // =================

    /**
     * 전체 헬스 체크
     */
    async healthCheck() {
        return this.get('/health');
    }
}

// 전역 API 클라이언트 인스턴스
const api = new ApiClient();

// 전역으로 노출
window.api = api;
