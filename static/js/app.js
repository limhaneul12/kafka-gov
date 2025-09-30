/**
 * 메인 애플리케이션 - Kafka Governance UI
 */

class KafkaGovApp {
    constructor() {
        this.currentTab = 'dashboard';
        this.selectedFiles = [];
        this.init();
    }

    /**
     * 애플리케이션 초기화
     */
    init() {
        this.setupEventListeners();
        this.loadDashboard();
        
        // WebSocket 초기화 (실시간 업데이트용)
        try {
            initializeWebSocket();
        } catch (error) {
            console.warn('WebSocket 초기화 실패:', error);
        }
        
        // 주기적 데이터 업데이트 (5분마다)
        setInterval(() => {
            if (this.currentTab === 'dashboard') {
                this.loadDashboard();
            }
        }, 300000);
    }


    /**
     * 이벤트 리스너 설정
     */
    setupEventListeners() {
        // 탭 네비게이션
        document.querySelectorAll('.nav-link').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const tab = e.currentTarget.dataset.tab;
                this.switchTab(tab);
            });
        });

        // 모달 닫기
        document.querySelectorAll('.modal-close').forEach(btn => {
            btn.addEventListener('click', () => {
                Modal.hideAll();
            });
        });

        // 모달 배경 클릭으로 닫기
        document.querySelectorAll('.modal').forEach(modal => {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    Modal.hideAll();
                }
            });
        });

        // 토픽 생성 버튼
        document.getElementById('create-topic-btn').addEventListener('click', () => {
            Modal.show('create-topic-modal');
        });

        // 토픽 생성 폼
        document.getElementById('create-topic-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleCreateTopic();
        });

        // 토픽 생성 취소
        document.getElementById('cancel-topic').addEventListener('click', () => {
            Modal.hide('create-topic-modal');
            FormUtils.resetForm('create-topic-form');
        });

        // 스키마 업로드 버튼
        document.getElementById('upload-schema-btn').addEventListener('click', () => {
            Modal.show('upload-schema-modal');
        });

        // 스키마 업로드 폼
        document.getElementById('upload-schema-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleUploadSchema();
        });

        // 스키마 업로드 취소
        document.getElementById('cancel-schema').addEventListener('click', () => {
            Modal.hide('upload-schema-modal');
            FormUtils.resetForm('upload-schema-form');
            this.selectedFiles = [];
        });

        // 파일 선택
        document.getElementById('schema-files').addEventListener('change', (e) => {
            this.selectedFiles = Array.from(e.target.files);
            FileManager.renderSelectedFiles(this.selectedFiles, 'selected-files');
        });

        // 정책 초기화 버튼
        document.getElementById('init-policies-btn').addEventListener('click', () => {
            this.handleInitializePolicies();
        });

        // 필터 이벤트
        document.getElementById('topic-env-filter')?.addEventListener('change', () => {
            this.loadTopics();
        });

        document.getElementById('topic-search')?.addEventListener('input', 
            this.debounce(() => this.loadTopics(), 300)
        );

        document.getElementById('schema-search')?.addEventListener('input', 
            this.debounce(() => this.loadSchemas(), 300)
        );

        document.getElementById('schema-type-filter')?.addEventListener('change', () => {
            this.loadSchemas();
        });
    }

    /**
     * 탭 전환
     */
    switchTab(tabName) {
        // 네비게이션 업데이트
        document.querySelectorAll('.nav-link').forEach(link => {
            link.classList.remove('active');
        });
        document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');

        // 탭 컨텐츠 업데이트
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
        });
        document.getElementById(tabName).classList.add('active');

        this.currentTab = tabName;

        // 탭별 데이터 로드
        switch (tabName) {
            case 'dashboard':
                this.loadDashboard();
                break;
            case 'topics':
                this.loadTopics();
                break;
            case 'schemas':
                this.loadSchemas();
                break;
            case 'policies':
                this.loadPolicies();
                break;
        }
    }

    /**
     * 대시보드 데이터 로드
     */
    async loadDashboard() {
        try {
            // 통계 업데이트
            await StatsUpdater.updateDashboardStats();

            // 최근 활동 (모의 데이터)
            const activities = [
                {
                    action: 'create',
                    target: 'user-events',
                    message: '토픽이 생성되었습니다',
                    type: 'success',
                    timestamp: new Date(Date.now() - 5 * 60000)
                },
                {
                    action: 'violation',
                    target: 'payment-schema',
                    message: '에서 정책 위반 감지',
                    type: 'warning',
                    timestamp: new Date(Date.now() - 15 * 60000)
                },
                {
                    action: 'update',
                    target: 'order-topic',
                    message: '설정이 변경되었습니다',
                    type: 'success',
                    timestamp: new Date(Date.now() - 30 * 60000)
                }
            ];

            ActivityRenderer.renderRecentActivities(activities);

        } catch (error) {
            console.error('대시보드 로드 실패:', error);
            Toast.error('대시보드 데이터를 불러올 수 없습니다.');
        }
    }

    /**
     * 토픽 데이터 로드
     */
    async loadTopics() {
        try {
            Loading.show();

            // 필터 값 가져오기
            const envFilter = document.getElementById('topic-env-filter')?.value || '';
            const searchFilter = document.getElementById('topic-search')?.value || '';

            // 모의 토픽 데이터 (실제로는 API 호출)
            const topics = [
                {
                    name: 'user-events',
                    environment: 'dev',
                    partitions: 3,
                    replication_factor: 1,
                    owner: 'user-service',
                    status: 'active',
                    description: '사용자 이벤트 스트림'
                },
                {
                    name: 'payment-events',
                    environment: 'prod',
                    partitions: 6,
                    replication_factor: 3,
                    owner: 'payment-service',
                    status: 'active',
                    description: '결제 이벤트 스트림'
                },
                {
                    name: 'order-events',
                    environment: 'stg',
                    partitions: 3,
                    replication_factor: 2,
                    owner: 'order-service',
                    status: 'active',
                    description: '주문 이벤트 스트림'
                }
            ];

            // 필터 적용
            const filteredTopics = topics.filter(topic => {
                const matchesEnv = !envFilter || topic.environment === envFilter;
                const matchesSearch = !searchFilter || 
                    topic.name.toLowerCase().includes(searchFilter.toLowerCase());
                return matchesEnv && matchesSearch;
            });

            TableRenderer.renderTopicsTable(filteredTopics);

        } catch (error) {
            console.error('토픽 로드 실패:', error);
            Toast.error('토픽 데이터를 불러올 수 없습니다.');
        } finally {
            Loading.hide();
        }
    }

    /**
     * 스키마 데이터 로드
     */
    async loadSchemas() {
        try {
            Loading.show();

            // 필터 값 가져오기
            const searchFilter = document.getElementById('schema-search')?.value || '';
            const typeFilter = document.getElementById('schema-type-filter')?.value || '';

            // 모의 스키마 데이터
            const schemas = [
                {
                    subject: 'user-events-value',
                    version: 1,
                    schema_type: 'AVRO',
                    compatibility: 'BACKWARD',
                    registered_at: '2024-01-15T10:30:00Z',
                    id: 'schema_001'
                },
                {
                    subject: 'payment-events-value',
                    version: 2,
                    schema_type: 'JSON',
                    compatibility: 'FULL',
                    registered_at: '2024-01-10T14:20:00Z',
                    id: 'schema_002'
                },
                {
                    subject: 'order-events-value',
                    version: 1,
                    schema_type: 'AVRO',
                    compatibility: 'BACKWARD',
                    registered_at: '2024-01-12T09:15:00Z',
                    id: 'schema_003'
                }
            ];

            // 필터 적용
            const filteredSchemas = schemas.filter(schema => {
                const matchesSearch = !searchFilter || 
                    schema.subject.toLowerCase().includes(searchFilter.toLowerCase());
                const matchesType = !typeFilter || schema.schema_type === typeFilter;
                return matchesSearch && matchesType;
            });

            TableRenderer.renderSchemasTable(filteredSchemas);

        } catch (error) {
            console.error('스키마 로드 실패:', error);
            Toast.error('스키마 데이터를 불러올 수 없습니다.');
        } finally {
            Loading.hide();
        }
    }

    /**
     * 정책 데이터 로드
     */
    async loadPolicies() {
        try {
            Loading.show();

            // 정책 위반 데이터 (모의)
            const violations = [
                {
                    target: 'test-topic-123',
                    severity: 'ERROR',
                    message: '토픽명이 네이밍 규칙을 위반했습니다. 소문자와 하이픈만 사용하세요.'
                },
                {
                    target: 'user_events',
                    severity: 'WARNING',
                    message: '언더스코어 사용이 권장되지 않습니다. 하이픈을 사용하세요.'
                }
            ];

            ActivityRenderer.renderViolations(violations);

        } catch (error) {
            console.error('정책 로드 실패:', error);
            Toast.error('정책 데이터를 불러올 수 없습니다.');
        } finally {
            Loading.hide();
        }
    }

    /**
     * 토픽 생성 처리
     */
    async handleCreateTopic() {
        try {
            if (!FormUtils.validateForm('create-topic-form')) {
                Toast.warning('필수 필드를 모두 입력해주세요.');
                return;
            }

            Loading.show();

            const formData = FormUtils.formToObject(document.getElementById('create-topic-form'));
            
            // 토픽 배치 요청 구성
            const batch = {
                environment: formData['topic-env'],
                specs: [{
                    name: formData['topic-name'],
                    action: 'CREATE',
                    config: {
                        'num.partitions': formData['topic-partitions'],
                        'replication.factor': formData['topic-replication']
                    },
                    metadata: {
                        description: formData['topic-description'] || '',
                        owner: 'admin',
                        sla: 'standard'
                    }
                }]
            };

            // Dry-run 먼저 실행
            const dryRunResult = await api.topicBatchDryRun(batch);
            
            if (dryRunResult.violations && dryRunResult.violations.length > 0) {
                const errorMessages = dryRunResult.violations.map(v => v.message).join('\n');
                Toast.error(`정책 위반:\n${errorMessages}`);
                return;
            }

            // 실제 적용
            const result = await api.topicBatchApply(batch);
            
            if (result.success_count > 0) {
                Toast.success('토픽이 성공적으로 생성되었습니다.');
                Modal.hide('create-topic-modal');
                FormUtils.resetForm('create-topic-form');
                
                // 토픽 목록 새로고침
                if (this.currentTab === 'topics') {
                    this.loadTopics();
                }
            } else {
                Toast.error('토픽 생성에 실패했습니다.');
            }

        } catch (error) {
            console.error('토픽 생성 실패:', error);
            Toast.error(`토픽 생성 실패: ${error.message}`);
        } finally {
            Loading.hide();
        }
    }

    /**
     * 스키마 업로드 처리
     */
    async handleUploadSchema() {
        try {
            if (this.selectedFiles.length === 0) {
                Toast.warning('업로드할 파일을 선택해주세요.');
                return;
            }

            // 파일 검증
            const allowedTypes = ['.avsc', '.json', '.proto'];
            const maxSize = 10 * 1024 * 1024; // 10MB

            for (const file of this.selectedFiles) {
                if (!FileManager.validateFileType(file, allowedTypes)) {
                    Toast.error(`지원하지 않는 파일 형식입니다: ${file.name}`);
                    return;
                }
                if (!FileManager.validateFileSize(file, maxSize)) {
                    Toast.error(`파일 크기가 너무 큽니다: ${file.name}`);
                    return;
                }
            }

            Loading.show();

            // 파일 업로드
            const result = await api.uploadSchemaFiles(this.selectedFiles);
            
            if (result.success_count > 0) {
                Toast.success(`${result.success_count}개 스키마가 성공적으로 업로드되었습니다.`);
                Modal.hide('upload-schema-modal');
                FormUtils.resetForm('upload-schema-form');
                this.selectedFiles = [];
                
                // 스키마 목록 새로고침
                if (this.currentTab === 'schemas') {
                    this.loadSchemas();
                }
            } else {
                Toast.error('스키마 업로드에 실패했습니다.');
            }

        } catch (error) {
            console.error('스키마 업로드 실패:', error);
            Toast.error(`스키마 업로드 실패: ${error.message}`);
        } finally {
            Loading.hide();
        }
    }

    /**
     * 정책 초기화 처리
     */
    async handleInitializePolicies() {
        try {
            if (!confirm('기본 정책을 초기화하시겠습니까?')) {
                return;
            }

            Loading.show();

            await api.initializePolicies();
            Toast.success('기본 정책이 초기화되었습니다.');
            
            // 정책 목록 새로고침
            if (this.currentTab === 'policies') {
                this.loadPolicies();
            }

        } catch (error) {
            console.error('정책 초기화 실패:', error);
            Toast.error(`정책 초기화 실패: ${error.message}`);
        } finally {
            Loading.hide();
        }
    }

    /**
     * 디바운스 유틸리티
     */
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
}

// =================
// 전역 함수들 (테이블 액션용)
// =================

/**
 * 토픽 상세 보기
 */
async function viewTopicDetail(topicName) {
    try {
        Loading.show();
        const detail = await api.getTopicDetail(topicName);
        
        // 상세 정보 모달 표시 (구현 필요)
        console.log('토픽 상세:', detail);
        Toast.info(`${topicName} 상세 정보를 조회했습니다.`);
        
    } catch (error) {
        console.error('토픽 상세 조회 실패:', error);
        Toast.error('토픽 상세 정보를 불러올 수 없습니다.');
    } finally {
        Loading.hide();
    }
}

/**
 * 토픽 편집
 */
function editTopic(topicName) {
    Toast.info(`${topicName} 편집 기능은 준비 중입니다.`);
}

/**
 * 토픽 삭제
 */
async function deleteTopic(topicName) {
    if (!confirm(`정말로 ${topicName} 토픽을 삭제하시겠습니까?`)) {
        return;
    }
    
    try {
        Loading.show();
        
        // 삭제 배치 요청 (구현 필요)
        Toast.warning('토픽 삭제 기능은 준비 중입니다.');
        
    } catch (error) {
        console.error('토픽 삭제 실패:', error);
        Toast.error('토픽 삭제에 실패했습니다.');
    } finally {
        Loading.hide();
    }
}

/**
 * 스키마 상세 보기
 */
function viewSchemaDetail(subject) {
    Toast.info(`${subject} 상세 정보 기능은 준비 중입니다.`);
}

/**
 * 스키마 다운로드
 */
function downloadSchema(subject) {
    Toast.info(`${subject} 다운로드 기능은 준비 중입니다.`);
}

/**
 * 스키마 삭제
 */
function deleteSchema(subject) {
    if (!confirm(`정말로 ${subject} 스키마를 삭제하시겠습니까?`)) {
        return;
    }
    
    Toast.warning('스키마 삭제 기능은 준비 중입니다.');
}

/**
 * 파일 제거
 */
function removeFile(index) {
    const app = window.kafkaGovApp;
    if (app) {
        app.selectedFiles.splice(index, 1);
        FileManager.renderSelectedFiles(app.selectedFiles, 'selected-files');
        
        // 파일 input 업데이트
        const fileInput = document.getElementById('schema-files');
        const dt = new DataTransfer();
        app.selectedFiles.forEach(file => dt.items.add(file));
        fileInput.files = dt.files;
    }
}

// =================
// 애플리케이션 시작
// =================
document.addEventListener('DOMContentLoaded', () => {
    window.kafkaGovApp = new KafkaGovApp();
});
