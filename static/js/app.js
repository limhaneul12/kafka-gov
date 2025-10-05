/**
 * 메인 애플리케이션 - Kafka Governance UI
 */

class KafkaGovApp {
    constructor() {
        this.currentTab = 'dashboard';
        this.selectedFiles = [];
        this.init();
    }

    init() {
        console.log('KafkaGovApp 초기화 시작...');
        this.setupEventListeners();
        // 초기 배치 아이템 리스너 연결
        const firstItem = document.getElementById('batch-items')?.firstElementChild;
        if (firstItem && firstItem.classList.contains('batch-item')) {
            this.attachBatchItemListeners(firstItem);
        }
        // 초기 탭 로딩
        console.log('초기 탭 전환:', this.currentTab);
        this.switchTab(this.currentTab);
    }

    /**
     * 배치 작업 아이템 템플릿 생성
     */
    createBatchItemTemplate() {
        return `
            <div class="batch-item">
                <div class="batch-item-row batch-item-header">
                    <label>
                        작업
                        <select class="batch-action">
                            <option value="CREATE">생성</option>
                            <option value="UPDATE">수정</option>
                            <option value="UPSERT">업서트</option>
                            <option value="DELETE">삭제</option>
                        </select>
                    </label>
                    <button type="button" class="btn-icon remove-batch-item" title="행 제거">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
                <div class="batch-item-row">
                    <label>토픽명
                        <input type="text" class="batch-topic-name" placeholder="env.topic.name" required>
                    </label>
                    <label>파티션
                        <input type="number" class="batch-partitions" min="1" value="3" required>
                    </label>
                    <label>복제
                        <input type="number" class="batch-replication" min="1" value="3" required>
                    </label>
                </div>
                <div class="batch-item-row metadata-fields">
                    <label>소유자
                        <input type="text" class="batch-owner" placeholder="team-service" required>
                    </label>
                    <label>문서 URL
                        <input type="url" class="batch-doc" placeholder="https://...">
                    </label>
                </div>
                <div class="batch-item-row metadata-fields">
                    <label>태그
                        <input type="text" class="batch-tags" placeholder="tag1, tag2">
                    </label>
                </div>
                <div class="batch-item-row reason-field hidden">
                    <label>삭제 사유
                        <textarea class="batch-reason" rows="2" placeholder="삭제 사유를 입력하세요"></textarea>
                    </label>
                </div>
            </div>
        `;
    }

    /**
     * 배치 아이템 리스너 연결
     */
    attachBatchItemListeners(item) {
        const actionSelect = item.querySelector('.batch-action');
        const reasonField = item.querySelector('.reason-field');

        actionSelect.addEventListener('change', () => {
            const action = actionSelect.value;
            const metadataFields = item.querySelectorAll('.metadata-fields');

            if (action === 'DELETE') {
                reasonField.classList.remove('hidden');
                metadataFields.forEach((el) => el.classList.add('hidden'));
            } else {
                reasonField.classList.add('hidden');
                metadataFields.forEach((el) => el.classList.remove('hidden'));
            }
        });
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

        // 단일 토픽 생성 버튼
        document.getElementById('create-single-topic-btn')?.addEventListener('click', () => {
            Modal.show('create-single-topic-modal');
        });

        // 단일 토픽 생성 폼 제출
        document.getElementById('create-single-topic-form')?.addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleSingleTopicCreate();
        });

        // 배치 작업 버튼
        document.getElementById('batch-topic-btn').addEventListener('click', () => {
            Modal.show('batch-topic-modal');
        });

        // 배치 입력 방식 탭 전환
        document.querySelectorAll('.batch-input-tab').forEach(tab => {
            tab.addEventListener('click', (e) => {
                const inputType = e.currentTarget.dataset.input;
                this.switchBatchInputTab(inputType);
            });
        });

        // YAML 파일 업로드
        document.getElementById('batch-yaml-file')?.addEventListener('change', (e) => {
            this.handleYAMLFileUpload(e);
        });

        // 배치 작업 추가 버튼
        document.getElementById('add-batch-item')?.addEventListener('click', () => {
            this.addBatchItem();
        });

        // 배치 아이템 제거 이벤트 위임
        document.getElementById('batch-items')?.addEventListener('click', (e) => {
            const removeBtn = e.target.closest('.remove-batch-item');
            if (removeBtn) {
                const item = removeBtn.closest('.batch-item');
                if (document.querySelectorAll('.batch-item').length > 1) {
                    item.remove();
                } else {
                    Toast.warning('최소 1개의 작업이 필요합니다.');
                }
            }
        });

        // Dry Run 실행 버튼
        document.getElementById('run-dry-run')?.addEventListener('click', () => {
            this.handleBatchDryRun();
        });

        // Apply 버튼
        document.getElementById('apply-batch')?.addEventListener('click', () => {
            this.handleBatchApply();
        });

        // 배치 탭 전환
        document.querySelectorAll('.batch-tab').forEach(tab => {
            tab.addEventListener('click', (e) => {
                const tabName = e.currentTarget.dataset.tab;
                this.switchBatchTab(tabName);
            });
        });

        // 스키마 삭제 분석 버튼
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('analyze-delete-btn')) {
                const subject = e.target.dataset.subject;
                this.handleSchemaDeleteAnalysis(subject);
            }
        });

        // 배치 작업 취소
        document.getElementById('cancel-batch').addEventListener('click', () => {
            Modal.hide('batch-topic-modal');
        });

        // 동기화 버튼들
        document.getElementById('sync-topics-btn')?.addEventListener('click', async () => {
            await this.syncTopics();
        });

        document.getElementById('sync-schemas-btn')?.addEventListener('click', async () => {
            await this.syncSchemas();
        });

        // 스키마 업로드 버튼
        document.getElementById('upload-schema-btn')?.addEventListener('click', () => {
            Modal.show('upload-schema-modal');
        });

        // 토픽 생성 버튼들
        document.getElementById('create-single-topic-btn')?.addEventListener('click', () => {
            Modal.show('create-single-topic-modal');
        });

        // 스키마 업로드 폼
        document.getElementById('upload-schema-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleUploadSchema();
        });

        // 강제 삭제 버튼 이벤트
        document.getElementById('force-delete-schema').addEventListener('click', () => {
            const subject = document.getElementById('force-delete-schema').dataset.subject;
            if (confirm(`정말로 ${subject} 스키마를 강제 삭제하시겠습니까?`)) {
                this.handleForceDeleteSchema(subject);
            }
        });

        // 파일 선택
        document.getElementById('schema-files').addEventListener('change', (e) => {
            this.selectedFiles = Array.from(e.target.files);
            FileManager.renderSelectedFiles(this.selectedFiles, 'selected-files');
        });


        // 삭제 분석 취소 버튼
        document.getElementById('cancel-delete-analysis')?.addEventListener('click', () => {
            Modal.hide('schema-delete-modal');
        });

        // 최근 활동 새로고침 버튼
        document.getElementById('refresh-activities-btn')?.addEventListener('click', async () => {
            try {
                Loading.show();
                const activities = await api.getRecentActivities(10);
                ActivityRenderer.renderRecentActivities(activities);
                Toast.success('최근 활동이 새로고침되었습니다.');
            } catch (error) {
                console.error('활동 새로고침 실패:', error);
                Toast.error('활동을 새로고침할 수 없습니다.');
            } finally {
                Loading.hide();
            }
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

        document.getElementById('schema-env-filter')?.addEventListener('change', () => {
            this.loadSchemas();
        });

        // 토픽 전체 선택
        document.getElementById('topic-select-all')?.addEventListener('change', (e) => {
            const checkboxes = document.querySelectorAll('.topic-checkbox');
            checkboxes.forEach(cb => cb.checked = e.target.checked);
            this.handleTopicCheckboxChange();
        });

        // 토픽 일괄 삭제
        document.getElementById('bulk-delete-topics-btn')?.addEventListener('click', () => {
            this.handleBulkDeleteTopics();
        });
    }

    /**
     * 탭 전환
     */
    async switchTab(tabName) {
        console.log('탭 전환 시작:', tabName);
        
        // 네비게이션 업데이트
        document.querySelectorAll('.nav-link').forEach(link => {
            link.classList.remove('active');
        });
        const navLink = document.querySelector(`[data-tab="${tabName}"]`);
        if (navLink) {
            navLink.classList.add('active');
            console.log('네비게이션 업데이트 완료');
        } else {
            console.error('네비게이션 링크를 찾을 수 없음:', tabName);
        }

        // 탭 컨텐츠 업데이트
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
        });
        const tabContent = document.getElementById(tabName);
        if (tabContent) {
            tabContent.classList.add('active');
            console.log('탭 컨텐츠 활성화 완료');
        } else {
            console.error('탭 컨텐츠를 찾을 수 없음:', tabName);
        }

        this.currentTab = tabName;

        // 탭별 데이터 로드
        console.log('데이터 로딩 시작...');
        switch (tabName) {
            case 'dashboard':
                await this.loadDashboard();
                break;
            case 'topics':
                await this.loadTopics();
                break;
            case 'schemas':
                await this.loadSchemas();
                break;
        }
    }

    /**
     * 대시보드 데이터 로드
     */
    async loadDashboard() {
        try {
            Loading.show();
            console.log('대시보드 로딩 시작...');

            // 개별 API 호출 (병렬 처리)
            const [topicCount, schemaCount, correlations, activities, clusterStatus] = await Promise.all([
                api.getTopicCount().catch(err => { console.error('토픽 카운트 실패:', err); return { count: 0 }; }),
                api.getSchemaCount().catch(err => { console.error('스키마 카운트 실패:', err); return { count: 0 }; }),
                api.getAllCorrelations().catch(err => { console.error('상관관계 조회 실패:', err); return []; }),
                api.getRecentActivities(10).catch(err => { console.error('최근 활동 조회 실패:', err); return []; }),
                api.getClusterStatus().catch(err => { console.error('클러스터 상태 조회 실패:', err); return null; })
            ]);

            console.log('API 응답:', { topicCount, schemaCount, correlations: correlations.length, activities: activities.length, clusterStatus });

            // 통계 업데이트
            const topicCountEl = document.getElementById('topic-count');
            const schemaCountEl = document.getElementById('schema-count');
            const correlationCountEl = document.getElementById('correlation-count');
            
            if (topicCountEl) topicCountEl.textContent = topicCount.count;
            if (schemaCountEl) schemaCountEl.textContent = schemaCount.count;
            if (correlationCountEl) correlationCountEl.textContent = correlations.length || 0;

            // 클러스터 상태 렌더링
            ActivityRenderer.renderClusterStatus(clusterStatus);

            // 최근 활동 렌더링
            ActivityRenderer.renderRecentActivities(activities);

            console.log('대시보드 로딩 완료');

        } catch (error) {
            console.error('대시보드 로드 실패:', error);
            Toast.error('대시보드 데이터를 불러올 수 없습니다.');
        } finally {
            Loading.hide();
        }
    }

    /**
     * 환경별 상태 렌더링
     */
    renderEnvironmentStatus(correlations) {
        const container = document.getElementById('environment-status');
        if (!container) return;

        const envGroups = correlations.reduce((acc, corr) => {
            const env = corr.environment || 'unknown';
            acc[env] = (acc[env] || 0) + 1;
            return acc;
        }, {});

        const html = Object.entries(envGroups)
            .map(([env, count]) => `
                <div class="env-item">
                    <span class="env-label">${env.toUpperCase()}</span>
                    <span class="env-count">${count}개 토픽</span>
                </div>
            `)
            .join('');

        container.innerHTML = html || '<p style="text-align: center; color: var(--text-muted);">환경 정보가 없습니다.</p>';
    }

    /**
     * 토픽 목록 로드 (실제 Kafka 토픽 + 상관관계)
     */
    async loadTopics() {
        try {
            Loading.show();
            const envFilter = document.getElementById('topic-env-filter')?.value ?? '';
            const searchFilter = document.getElementById('topic-search')?.value ?? '';

            // 실제 토픽 목록 조회
            const topicsData = await api.getTopics();
            const topics = topicsData.topics || [];

            // 토픽 데이터 매핑
            const mapped = topics.map(topic => ({
                topic_name: topic.name,
                owner: topic.owner,
                tags: topic.tags || [],
                partition_count: topic.partition_count,
                replication_factor: topic.replication_factor,
                environment: topic.environment,
            }));

            const filtered = mapped.filter((item) => {
                const envMatches = !envFilter || item.environment === envFilter;
                const sf = (searchFilter || '').toLowerCase();
                const searchMatches = !sf || item.topic_name.toLowerCase().includes(sf);
                return envMatches && searchMatches;
            });

            TableRenderer.renderTopicsTable(filtered);
        } catch (error) {
            console.error('토픽 로드 실패:', error);
            Toast.error(`토픽 목록 조회 실패: ${error.message}`);
        } finally {
            Loading.hide();
        }
    }

    /**
     * 스키마 연관 정보 로드
     */
    async loadSchemas() {
        try {
            Loading.show();

            const searchFilter = document.getElementById('schema-search')?.value ?? '';
            const typeFilter = document.getElementById('schema-type-filter')?.value ?? '';
            const envFilter = document.getElementById('schema-env-filter')?.value ?? '';

            // 스키마 아티팩트 조회
            const artifacts = await api.getSchemaArtifacts().catch(() => []);

            // 스키마별로 그룹핑
            const schemaGroups = {};
            
            // 아티팩트에서 기본 정보 생성
            artifacts.forEach((artifact) => {
                if (!schemaGroups[artifact.subject]) {
                    schemaGroups[artifact.subject] = {
                        subject: artifact.subject,
                        environments: new Set(),
                        latest_version: artifact.version,
                        schema_type: artifact.schema_type,
                    };
                }
                // 환경 추출 (subject에서)
                const env = artifact.subject.split('.')[0];
                if (['dev', 'stg', 'prod'].includes(env)) {
                    schemaGroups[artifact.subject].environments.add(env);
                }
            });

            // 요약 정보로 변환
            const subjects = Object.values(schemaGroups).map((group) => ({
                subject: group.subject,
                environments: Array.from(group.environments),
                schema_type: group.schema_type,
            }));

            const filtered = subjects.filter((subject) => {
                const matchesSearch = !searchFilter
                    || subject.subject.toLowerCase().includes(searchFilter.toLowerCase());
                
                // 타입 필터
                const matchesType = !typeFilter || subject.schema_type === typeFilter;
                
                // 환경 필터
                const matchesEnv = !envFilter || subject.environments.includes(envFilter);
                
                return matchesSearch && matchesType && matchesEnv;
            });

            TableRenderer.renderSchemasTable(filtered, this);
        } catch (error) {
            console.error('스키마 로드 실패:', error);
            Toast.error(`스키마 목록 조회 실패: ${error.message}`);
        } finally {
            Loading.hide();
        }
    }


    /**
     * 토픽 동기화 (Kafka → DB)
     */
    async syncTopics() {
        try {
            Loading.show();
            
            // Kafka에서 모든 토픽 가져오기
            const topicsData = await api.getTopics();
            const topics = topicsData.topics || [];
            
            Toast.info(`${topics.length}개의 토픽을 찾았습니다. 동기화 중...`);
            
            // 목록 새로고침
            await this.loadTopics();
            
            Toast.success('토픽 동기화가 완료되었습니다.');
        } catch (error) {
            console.error('토픽 동기화 실패:', error);
            Toast.error(`토픽 동기화 실패: ${error.message}`);
        } finally {
            Loading.hide();
        }
    }

    /**
     * 스키마 동기화 (Schema Registry → DB)
     */
    async syncSchemas() {
        try {
            Loading.show();
            
            Toast.info('Schema Registry에서 스키마를 동기화하는 중...');
            
            // 실제 동기화 API 호출
            const result = await api.syncSchemas();
            
            // 목록 새로고침
            await this.loadSchemas();
            
            Toast.success(
                `스키마 동기화 완료! 총 ${result.total}개 (새로 추가: ${result.added}개, 업데이트: ${result.updated}개)`
            );
        } catch (error) {
            console.error('스키마 동기화 실패:', error);
            Toast.error(`스키마 동기화 실패: ${error.message}`);
        } finally {
            Loading.hide();
        }
    }

    /**
     * 스키마 삭제 처리
     */
    async handleSchemaDelete(subject) {
        if (!confirm(`정말로 스키마 "${subject}"를 삭제하시겠습니까?\n이 작업은 되돌릴 수 없습니다.`)) {
            return;
        }

        try {
            Loading.show();
            
            // 먼저 영향도 분석
            const impact = await api.analyzeSchemaDelete(subject);
            
            if (!impact.safe_to_delete) {
                const warnings = impact.warnings.join('\n- ');
                const proceed = confirm(
                    `⚠️ 경고: 이 스키마 삭제는 위험할 수 있습니다.\n\n경고 내용:\n- ${warnings}\n\n그래도 삭제하시겠습니까?`
                );
                if (!proceed) {
                    Toast.warning('스키마 삭제가 취소되었습니다.');
                    return;
                }
            }

            // 삭제 실행
            await api.deleteSchema(subject, 'TopicNameStrategy', !impact.safe_to_delete);
            
            Toast.success(`스키마 "${subject}"가 삭제되었습니다.`);
            
            // 목록 새로고침
            await this.loadSchemas();
            
        } catch (error) {
            console.error('스키마 삭제 실패:', error);
            Toast.error(`스키마 삭제 실패: ${error.message}`);
        } finally {
            Loading.hide();
        }
    }

    /**
     * 단일 토픽 생성 처리
     */
    async handleSingleTopicCreate() {
        try {
            Loading.show();

            const form = document.getElementById('create-single-topic-form');
            const formData = FormUtils.formToObject(form);

            // 토픽 이름 검증
            const topicName = formData['single-topic-name'];
            const topicNamePattern = /^[a-z0-9._-]+$/;
            if (!topicNamePattern.test(topicName)) {
                Toast.error('토픽 이름 형식이 올바르지 않습니다. 형식: 소문자, 숫자, ., _, - 만 사용 가능');
                return;
            }

            const batch = {
                kind: 'TopicBatch',
                env: formData['single-topic-env'],
                change_id: `single_${Date.now()}`,
                items: [{
                    name: topicName,
                    action: 'create',
                    config: {
                        partitions: parseInt(formData['single-topic-partitions']),
                        replication_factor: parseInt(formData['single-topic-replication']),
                        min_insync_replicas: parseInt(formData['single-topic-min-insync'])
                    },
                    metadata: {
                        owner: formData['single-topic-owner'],
                        doc: formData['single-topic-doc'] || 'https://wiki.example.com',
                        tags: formData['single-topic-tags'] ? 
                            formData['single-topic-tags'].split(',').map(t => t.trim()).filter(t => t) : []
                    }
                }]
            };

            // 바로 Apply 실행
            const result = await api.topicBatchApply(batch);
            
            Toast.success('토픽이 성공적으로 생성되었습니다!');
            Modal.hide('create-single-topic-modal');
            form.reset();
            
            // 토픽 목록 새로고침
            if (this.currentTab === 'topics') {
                await this.loadTopics();
            }

        } catch (error) {
            console.error('단일 토픽 생성 실패:', error);
            
            // Backend에서 이미 한글 메시지로 변환되어 옴
            const errorMsg = error.message || '알 수 없는 오류가 발생했습니다.';
            Toast.error(errorMsg);
        } finally {
            Loading.hide();
        }
    }

    /**
     * 배치 입력 탭 전환
     */
    switchBatchInputTab(inputType) {
        // 탭 버튼 활성화
        document.querySelectorAll('.batch-input-tab').forEach(tab => {
            tab.classList.toggle('active', tab.dataset.input === inputType);
        });

        // 컨텐츠 표시
        document.querySelectorAll('.batch-input-content').forEach(content => {
            content.classList.remove('active');
        });
        document.getElementById(`${inputType}-input`)?.classList.add('active');
    }

    /**
     * YAML 파일 업로드 처리 (백엔드로 전송 및 즉시 적용)
     */
    async handleYAMLFileUpload(event) {
        const file = event.target.files[0];
        if (!file) return;

        if (!confirm('YAML 파일을 업로드하고 즉시 적용하시겠습니까?')) {
            event.target.value = ''; // 파일 선택 초기화
            return;
        }

        try {
            Loading.show();
            
            // 백엔드로 YAML 파일 전송 (안전한 파싱 및 즉시 적용)
            const result = await api.topicBatchUpload(file);
            
            // 결과 표시
            const summary = `
                <div class="apply-result">
                    <h4>적용 완료</h4>
                    <p><strong>적용됨:</strong> ${result.applied?.length || 0}개</p>
                    <p><strong>건너뜀:</strong> ${result.skipped?.length || 0}개</p>
                    <p><strong>실패:</strong> ${result.failed?.length || 0}개</p>
                    <p><strong>요약:</strong> ${result.summary || ''}</p>
                </div>
            `;
            
            document.getElementById('yaml-preview').style.display = 'block';
            document.getElementById('yaml-preview-content').innerHTML = summary;
            
            Toast.success(`YAML 배치 작업이 완료되었습니다! ${result.summary || ''}`);
            
            // 토픽 목록 새로고침
            if (this.currentTab === 'topics') {
                await this.loadTopics();
            }
            
            // 파일 선택 초기화
            event.target.value = '';
            
        } catch (error) {
            console.error('YAML 업로드 실패:', error);
            Toast.error(`YAML 업로드 실패: ${error.message}`);
            event.target.value = '';
        } finally {
            Loading.hide();
        }
    }

    /**
     * 간단한 YAML 파서 (실제로는 js-yaml 라이브러리 사용 권장)
     */
    parseYAML(text) {
        try {
            // JSON으로 변환 시도 (YAML은 JSON의 슈퍼셋)
            return JSON.parse(text);
        } catch {
            // 간단한 YAML 파싱 (매우 기본적인 구현)
            Toast.warning('복잡한 YAML은 지원하지 않습니다. JSON 형식을 사용하세요.');
            throw new Error('YAML 파싱 실패. JSON 형식을 사용하세요.');
        }
    }

    /**
     * 배치 작업 Dry Run 처리
     */
    async handleBatchDryRun() {
        try {
            Loading.show();

            let batch;

            // YAML 업로드 모드인지 확인
            const yamlInput = document.getElementById('yaml-input');
            if (yamlInput && yamlInput.classList.contains('active')) {
                // YAML 데이터 사용
                if (!this.currentYAMLBatch) {
                    Toast.warning('YAML 파일을 먼저 업로드해주세요.');
                    Loading.hide();
                    return;
                }
                batch = this.currentYAMLBatch;
            } else {
                // 수동 입력 데이터 사용
                if (!FormUtils.validateForm('batch-dry-run-form')) {
                    Toast.warning('필수 필드를 모두 입력해주세요.');
                    Loading.hide();
                    return;
                }

                const formData = FormUtils.formToObject(document.getElementById('batch-dry-run-form'));
                
                // 배치 작업 구성
                const batchItems = document.querySelectorAll('.batch-item');
                const items = [];
            
                batchItems.forEach(item => {
                const action = item.querySelector('.batch-action')?.value.toLowerCase(); // 소문자로 변환
                const topicName = item.querySelector('.batch-topic-name')?.value.trim();
                const partitions = item.querySelector('.batch-partitions')?.value;
                const replication = item.querySelector('.batch-replication')?.value;
                const owner = item.querySelector('.batch-owner')?.value.trim() || '';
                const sla = item.querySelector('.batch-sla')?.value.trim() || '';
                const doc = item.querySelector('.batch-doc')?.value.trim() || '';
                const tags = item.querySelector('.batch-tags')?.value.trim() || '';
                const reason = item.querySelector('.batch-reason')?.value.trim() || '';
                
                const topicItem = {
                    name: topicName,
                    action: action,
                };
                
                // DELETE가 아닌 경우 config와 metadata 필수
                if (action !== 'delete') {
                    topicItem.config = {
                        partitions: parseInt(partitions),
                        replication_factor: parseInt(replication)
                    };
                    topicItem.metadata = {
                        owner: owner || 'admin',
                        sla: sla || 'standard',
                        doc: doc || 'https://wiki.example.com', // 빈 문자열 대신 기본값
                        tags: tags ? tags.split(',').map(t => t.trim()).filter(t => t) : []
                    };
                }
                
                // DELETE인 경우 reason 필수
                if (action === 'delete' && reason) {
                    topicItem.reason = reason;
                }
                
                    items.push(topicItem);
                });

                batch = {
                    kind: 'TopicBatch',
                    env: formData['batch-env'],
                    change_id: formData['batch-change-id'],
                    items: items
                };
            }

            // Dry-run 실행
            const result = await api.topicBatchDryRun(batch);
            
            if (result.violations && result.violations.length > 0) {
                const errorMessages = result.violations.map(v => v.message).join('\n');
                Toast.error(`정책 위반:\n${errorMessages}`);
                return;
            }

            // 성공 시 적용 탭으로 전환
            this.currentBatchResult = batch;
            this.currentBatchPlan = result;
            this.switchBatchTab('apply');
            this.renderBatchResults(result);
            
            // Apply 버튼 표시
            document.getElementById('run-dry-run').style.display = 'none';
            document.getElementById('apply-batch').style.display = 'inline-block';
            
            Toast.success('Dry Run이 성공적으로 완료되었습니다.');

        } catch (error) {
            console.error('배치 Dry Run 실패:', error);
            Toast.error(`배치 Dry Run 실패: ${error.message}`);
        } finally {
            Loading.hide();
        }
    }

    /**
     * 배치 작업 적용 처리
     */
    async handleBatchApply() {
        try {
            if (!this.currentBatchResult || !this.currentBatchPlan) {
                Toast.warning('먼저 Dry Run을 실행해주세요.');
                return;
            }

            if (!confirm('변경사항을 적용하시겠습니까?')) {
                return;
            }

            Loading.show();

            const response = await api.topicBatchApply(this.currentBatchResult);

            if (response.applied?.length) {
                Toast.success(`${response.applied.length}개의 토픽 변경사항이 적용되었습니다.`);
                Modal.hide('batch-topic-modal');
                this.resetBatchForm();

                if (this.currentTab === 'topics') {
                    await this.loadTopics();
                }
            } else {
                Toast.error('변경사항 적용에 실패했습니다.');
            }

        } catch (error) {
            console.error('배치 적용 실패:', error);
            Toast.error(`배치 적용 실패: ${error.message}`);
        } finally {
            Loading.hide();
        }
    }

    /**
     * 배치 작업 폼 초기화
     */
    resetBatchForm() {
        document.getElementById('batch-env').value = '';
        document.getElementById('batch-change-id').value = '';
        document.getElementById('batch-items').innerHTML = this.createBatchItemTemplate();
        this.currentBatchResult = null;
        this.currentBatchPlan = null;
        this.switchBatchTab('dry-run');
        document.getElementById('run-dry-run').style.display = 'inline-block';
        document.getElementById('apply-batch').style.display = 'none';
        const firstItem = document.getElementById('batch-items').firstElementChild;
        if (firstItem) this.attachBatchItemListeners(firstItem);
    }

    /**
     * 배치 작업 아이템 추가
     */
    addBatchItem() {
        const batchItems = document.getElementById('batch-items');
        const wrapper = document.createElement('div');
        wrapper.innerHTML = this.createBatchItemTemplate().trim();
        const newItem = wrapper.firstElementChild;
        batchItems.appendChild(newItem);
        this.attachBatchItemListeners(newItem);
    }

    /**
     * 배치 탭 전환
     */
    switchBatchTab(tabName) {
        // 탭 버튼 업데이트
        document.querySelectorAll('.batch-tab').forEach(tab => {
            tab.classList.remove('active');
        });
        document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');

        // 탭 컨텐츠 업데이트
        document.querySelectorAll('.batch-tab-content').forEach(content => {
            content.classList.remove('active');
        });
        document.getElementById(`${tabName}-tab`).classList.add('active');
    }

    /**
     * 배치 결과 렌더링
     */
    renderBatchResults(result) {
        const resultsContainer = document.getElementById('plan-results');
        
        let html = `
            <div class="plan-summary">
                <h4>Dry Run 결과</h4>
                <div class="plan-stats">
                    <div class="stat-item">
                        <span class="stat-label">총 작업:</span>
                        <span class="stat-value">${result.plan?.length || 0}</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-label">위반 사항:</span>
                        <span class="stat-value">${result.violations?.length || 0}</span>
                    </div>
                </div>
            </div>
        `;

        if (result.plan && result.plan.length > 0) {
            html += '<div class="plan-details"><ul>';
            result.plan.forEach(item => {
                html += `
                    <li class="plan-item ${item.action.toLowerCase()}">
                        <strong>${item.name}</strong> - ${item.action}
                    </li>
                `;
            });
            html += '</ul></div>';
        }

        resultsContainer.innerHTML = html;
    }

    /**
     * 스키마 삭제 영향도 분석 처리
     */
    async handleSchemaDeleteAnalysis(subject) {
        try {
            Loading.show();
            
            // 영향도 분석 실행
            const analysis = await api.analyzeSchemaDelete(subject);
            
            // 분석 결과 모달에 표시
            this.renderDeleteAnalysisResults(subject, analysis);
            Modal.show('schema-delete-modal');
            
        } catch (error) {
            console.error('스키마 삭제 분석 실패:', error);
            Toast.error(`스키마 삭제 분석 실패: ${error.message}`);
        } finally {
            Loading.hide();
        }
    }

    /**
     * 삭제 분석 결과 렌더링
     */
    renderDeleteAnalysisResults(subject, analysis) {
        const resultsContainer = document.getElementById('delete-analysis-results');
        const forceDeleteBtn = document.getElementById('force-delete-schema');
        
        let html = `
            <div class="delete-analysis">
                <h4>Subject: ${subject}</h4>
                <div class="analysis-summary">
                    <div class="analysis-item">
                        <span class="label">현재 버전:</span>
                        <span class="value">${analysis.current_version}</span>
                    </div>
                    <div class="analysis-item">
                        <span class="label">전체 버전 수:</span>
                        <span class="value">${analysis.total_versions}</span>
                    </div>
                    <div class="analysis-item">
                        <span class="label">안전 삭제 가능:</span>
                        <span class="value ${analysis.safe_to_delete ? 'safe' : 'unsafe'}">
                            ${analysis.safe_to_delete ? '✅ 예' : '❌ 아니오'}
                        </span>
                    </div>
                </div>
        `;

        if (analysis.affected_topics && analysis.affected_topics.length > 0) {
            html += `
                <div class="affected-topics">
                    <h5>영향을 받는 토픽들 (${analysis.affected_topics.length}개):</h5>
                    <ul>
            `;
            analysis.affected_topics.forEach(topic => {
                html += `<li>${topic}</li>`;
            });
            html += `
                    </ul>
                </div>
            `;
        }

        if (analysis.warnings && analysis.warnings.length > 0) {
            html += `
                <div class="warnings">
                    <h5>⚠️ 경고사항들:</h5>
                    <ul>
            `;
            analysis.warnings.forEach(warning => {
                html += `<li>${warning}</li>`;
            });
            html += `
                    </ul>
                </div>
            `;
        }

        html += `
            </div>
        `;

        resultsContainer.innerHTML = html;
        
        // 강제 삭제 버튼 표시/숨김 결정
        if (!analysis.safe_to_delete) {
            forceDeleteBtn.style.display = 'inline-block';
            forceDeleteBtn.dataset.subject = subject;
        } else {
            forceDeleteBtn.style.display = 'none';
        }
    }

    /**
     * 강제 스키마 삭제 처리
     */
    async handleForceDeleteSchema(subject) {
        try {
            Loading.show();
            
            await api.deleteSchema(subject, 'TopicNameStrategy', true);
            Toast.success(`${subject} 스키마가 강제 삭제되었습니다.`);
            Modal.hide('schema-delete-modal');
            
            // 스키마 목록 새로고침
            if (this.currentTab === 'schemas') {
                await this.loadSchemas();
            }
            
        } catch (error) {
            console.error('스키마 강제 삭제 실패:', error);
            Toast.error(`스키마 강제 삭제 실패: ${error.message}`);
        } finally {
            Loading.hide();
        }
    }
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
            const env = document.getElementById('schema-env')?.value;
            const changeId = document.getElementById('schema-change-id')?.value;

            if (!env || !changeId) {
                Toast.warning('환경과 변경 ID를 입력해주세요.');
                return;
            }

            const result = await api.uploadSchemaFiles({
                env,
                changeId,
                files: this.selectedFiles,
            });
            
            // 응답 구조: { upload_id, artifacts: [], summary: { total_files, ... } }
            const totalFiles = result.summary?.total_files || result.artifacts?.length || 0;
            
            if (totalFiles > 0) {
                Toast.success(`${totalFiles}개 스키마가 성공적으로 업로드되었습니다.`);
                Modal.hide('upload-schema-modal');
                FormUtils.resetForm('upload-schema-form');
                this.selectedFiles = [];
                
                // 스키마 목록 새로고침
                if (this.currentTab === 'schemas') {
                    await this.loadSchemas();
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
     * 토픽 체크박스 변경 핸들러
     */
    handleTopicCheckboxChange() {
        const checkboxes = document.querySelectorAll('.topic-checkbox:checked');
        const count = checkboxes.length;
        const bulkDeleteBtn = document.getElementById('bulk-delete-topics-btn');
        const selectedCountSpan = document.getElementById('selected-count');
        
        if (count > 0) {
            bulkDeleteBtn.style.display = 'inline-flex';
            selectedCountSpan.textContent = count;
        } else {
            bulkDeleteBtn.style.display = 'none';
        }
    }

    /**
     * 토픽 일괄 삭제
     */
    async handleBulkDeleteTopics() {
        const checkboxes = document.querySelectorAll('.topic-checkbox:checked');
        const topicNames = Array.from(checkboxes).map(cb => cb.value);
        
        if (topicNames.length === 0) {
            Toast.warning('삭제할 토픽을 선택해주세요.');
            return;
        }

        if (!confirm(`선택한 ${topicNames.length}개의 토픽을 정말 삭제하시겠습니까?\n\n⚠️ 이 작업은 되돌릴 수 없습니다.\n\n삭제할 토픽:\n${topicNames.join('\n')}`)) {
            return;
        }

        try {
            Loading.show();
            const result = await api.bulkDeleteTopics(topicNames);
            
            if (result.succeeded && result.succeeded.length > 0) {
                Toast.success(`${result.succeeded.length}개 토픽이 삭제되었습니다.`);
            }
            if (result.failed && result.failed.length > 0) {
                Toast.warning(`${result.failed.length}개 토픽 삭제 실패: ${result.failed.join(', ')}`);
            }
            
            // 토픽 목록 새로고침
            await this.loadTopics();
            
            // 체크박스 초기화 (새로고침 후)
            document.getElementById('topic-select-all').checked = false;
            this.handleTopicCheckboxChange();
            
        } catch (error) {
            console.error('일괄 삭제 실패:', error);
            Toast.error(`토픽 일괄 삭제 실패: ${error.message}`);
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
 * 토픽 삭제
 */
async function deleteTopic(topicName) {
    if (!confirm(`토픽 "${topicName}"을(를) 정말 삭제하시겠습니까?\n\n⚠️ 이 작업은 되돌릴 수 없습니다.`)) {
        return;
    }

    try {
        Loading.show();
        await api.deleteTopic(topicName);
        Toast.success(`토픽 "${topicName}"이(가) 삭제되었습니다.`);
        
        // 토픽 목록 새로고침
        if (window.kafkaGovApp && window.kafkaGovApp.currentTab === 'topics') {
            await window.kafkaGovApp.loadTopics();
        }
    } catch (error) {
        console.error('토픽 삭제 실패:', error);
        Toast.error(`토픽 삭제 실패: ${error.message}`);
    } finally {
        Loading.hide();
    }
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
