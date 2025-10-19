/**
 * 메인 애플리케이션 - Kafka Governance UI
 */

class KafkaGovApp {
    constructor() {
        this.currentTab = 'dashboard';
        this.selectedFiles = [];
        this.activityRefreshInterval = null;
        // 현재 설정 추적
        this.lastSettings = api.getCurrentSettings();
        this.init();
    }

    init() {
        console.log('KafkaGovApp initialization...');
        this.setupEventListeners();
        this.setupSettingsWatcher();
        // 초기 배치 아이템 리스너 연결
        const firstItem = document.getElementById('batch-items')?.firstElementChild;
        if (firstItem && firstItem.classList.contains('batch-item')) {
            this.attachBatchItemListeners(firstItem);
        }
        // 초기 탭 로딩
        console.log('Initial tab switch:', this.currentTab);
        this.switchTab(this.currentTab);
        // 최근 활동 자동 갱신 시작 (30초마다)
        this.startActivityAutoRefresh();
    }

    /**
     * 설정 변경 감지 설정
     */
    setupSettingsWatcher() {
        // Detect settings change on window focus
        window.addEventListener('focus', () => {
            const currentSettings = api.getCurrentSettings();
            
            // 설정이 변경되었는지 확인
            if (this.lastSettings.clusterId !== currentSettings.clusterId ||
                this.lastSettings.registryId !== currentSettings.registryId ||
                this.lastSettings.storageId !== currentSettings.storageId ||
                this.lastSettings.connectId !== currentSettings.connectId) {
                
                console.log('Settings changed:', this.lastSettings, '->', currentSettings);
                this.lastSettings = currentSettings;
                
                // 현재 탭 데이터 새로고침
                this.refreshCurrentTab();
            }
        });

        // Storage 이벤트로 다른 탭에서의 변경 감지 (선택적)
        window.addEventListener('storage', (e) => {
            if (e.key && (e.key === 'currentClusterId' || 
                          e.key === 'currentRegistryId' || 
                          e.key === 'currentStorageId' ||
                          e.key === 'currentConnectId')) {
                console.log('Storage 이벤트 감지:', e.key, e.oldValue, '->', e.newValue);
                this.lastSettings = api.getCurrentSettings();
                this.refreshCurrentTab();
            }
        });
    }

    /**
     * 현재 탭 데이터 새로고침
     */
    async refreshCurrentTab() {
        console.log('현재 탭 새로고침:', this.currentTab);
        
        switch(this.currentTab) {
            case 'dashboard':
                await this.loadDashboard();
                break;
            case 'topics':
                await this.loadTopics();
                break;
            case 'schemas':
                await this.loadSchemas();
                break;
            case 'analytics':
                await this.loadAnalytics();
                break;
            case 'history':
                await this.loadHistory();
                break;
        }
        
        Toast.success('Settings changed. Data refreshed.');
    }

    /**
     * 배치 작업 아이템 템플릿 생성
     */
    createBatchItemTemplate() {
        return `
            <div class="batch-item">
                <div class="batch-item-row batch-item-header">
                    <label>
                        Action
                        <select class="batch-action">
                            <option value="CREATE">Create</option>
                            <option value="UPDATE">Update</option>
                            <option value="UPSERT">Upsert</option>
                            <option value="DELETE">Delete</option>
                        </select>
                    </label>
                    <button type="button" class="btn-icon remove-batch-item" title="Remove row">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
                <div class="batch-item-row">
                    <label>Topic
                        <input type="text" class="batch-topic-name" placeholder="env.topic.name" required>
                    </label>
                    <label>Partitions
                        <input type="number" class="batch-partitions" min="1" value="3" required>
                    </label>
                    <label>Replication
                        <input type="number" class="batch-replication" min="1" value="3" required>
                    </label>
                </div>
                <div class="batch-item-row metadata-fields">
                    <label>Owner
                        <input type="text" class="batch-owner" placeholder="team-service" required>
                    </label>
                    <label>Doc URL
                        <input type="url" class="batch-doc" placeholder="https://...">
                    </label>
                </div>
                <div class="batch-item-row metadata-fields">
                    <label>Tags
                        <input type="text" class="batch-tags" placeholder="tag1, tag2">
                    </label>
                </div>
                <div class="batch-item-row reason-field hidden">
                    <label>Delete Reason
                        <textarea class="batch-reason" rows="2" placeholder="Enter reason for deletion"></textarea>
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
        // 탭 네비게이션 (data-tab 속성이 있는 링크만)
        document.querySelectorAll('.nav-link[data-tab]').forEach(link => {
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

        // 클러스터 상태 새로고침 버튼
        document.getElementById('refresh-cluster-btn')?.addEventListener('click', async () => {
            try {
                Loading.show();
                const clusterStatus = await api.getClusterStatus();
                this.renderClusterStatus(clusterStatus);
                Toast.success('클러스터 상태가 새로고침되었습니다.');
            } catch (error) {
                console.error('클러스터 상태 새로고침 실패:', error);
                Toast.error('클러스터 상태를 새로고침할 수 없습니다.');
            } finally {
                Loading.hide();
            }
        });

        // 필터 이벤트
        document.getElementById('topic-env-filter')?.addEventListener('change', () => {
            this.loadTopics();
        });

        document.getElementById('topic-team-filter')?.addEventListener('change', () => {
            this.loadTopics();
        });

        document.getElementById('topic-tag-filter')?.addEventListener('change', () => {
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

        // 히스토리 검색 버튼
        document.getElementById('search-history-btn')?.addEventListener('click', () => {
            this.loadHistory();
        });

        // 히스토리 초기화 버튼
        document.getElementById('reset-history-btn')?.addEventListener('click', () => {
            document.getElementById('history-from-date').value = '';
            document.getElementById('history-to-date').value = '';
            document.getElementById('history-type-filter').value = '';
            document.getElementById('history-action-filter').value = '';
            document.getElementById('history-actor-filter').value = '';
            this.loadHistory();
        });
    }

    /**
     * 최근 활동 자동 갱신 시작
     */
    startActivityAutoRefresh() {
        // 기존 인터벌 정리
        if (this.activityRefreshInterval) {
            clearInterval(this.activityRefreshInterval);
        }
        
        // 30초마다 최근 활동 갱신
        this.activityRefreshInterval = setInterval(async () => {
            if (this.currentTab === 'dashboard') {
                try {
                    const activities = await api.getRecentActivities(10);
                    ActivityRenderer.renderRecentActivities(activities);
                    console.log('최근 활동 자동 갱신 완료');
                } catch (error) {
                    console.error('최근 활동 자동 갱신 실패:', error);
                }
            }
        }, 30000); // 30초
        
        console.log('최근 활동 자동 갱신 시작 (30초 간격)');
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
            case 'analytics':
                await this.loadAnalytics();
                break;
            case 'connectors':
                await this.loadConnectors();
                break;
            case 'history':
                await this.loadHistory();
                break;
        }
    }

    /**
     * Kafka Connect 커넥터 관리 로드
     */
    async loadConnectors() {
        if (typeof connectorManager !== 'undefined') {
            await connectorManager.init();
        }
    }

    /**
     * 대시보드 데이터 로드
     */
    async loadDashboard() {
        try {
            Loading.show();

            // 클러스터 선택 확인
            const settings = api.getCurrentSettings();
            if (!settings.clusterId || settings.clusterId === 'default') {
                Toast.warning('Settings에서 Kafka 클러스터를 먼저 선택해주세요.');
                this.renderDashboardMetrics([], 0);
                Loading.hide();
                return;
            }

            // 토픽과 스키마 데이터 가져오기
            const [topicsData, schemaCount, activities, clusterStatus] = await Promise.all([
                api.getTopics().catch(err => { console.error('토픽 조회 실패:', err); return { topics: [] }; }),
                api.getSchemaCount().catch(err => { console.error('스키마 카운트 실패:', err); return { count: 0 }; }),
                api.getRecentActivities(15).catch(err => { console.error('최근 활동 조회 실패:', err); return []; }),
                api.getClusterStatus().catch(err => { console.error('클러스터 상태 조회 실패:', err); return null; })
            ]);

            const topics = topicsData.topics || [];

            // 1. 메트릭 계산
            this.renderDashboardMetrics(topics, schemaCount.count);

            // 2. 환경별 분포 차트
            this.renderEnvDistribution(topics);

            // 3. Kafka 클러스터 상태
            this.renderClusterStatus(clusterStatus);

            // 4. 최근 활동
            this.renderRecentActivitiesList(activities);

        } catch (error) {
            console.error('대시보드 로드 실패:', error);
            Toast.error('대시보드 데이터를 불러올 수 없습니다.');
        } finally {
            Loading.hide();
        }
    }

    renderDashboardMetrics(topics, schemaCount) {
        const totalTopics = topics.length;
        const prodTopics = topics.filter(t => t.environment === 'prod').length;
        const teams = [...new Set(topics.map(t => t.owner).filter(o => o))];
        const tags = [...new Set(topics.flatMap(t => t.tags || []))];

        document.getElementById('metric-total-topics').textContent = totalTopics;
        document.getElementById('metric-topics-change').textContent = '전체 토픽';

        document.getElementById('metric-total-schemas').textContent = schemaCount;
        document.getElementById('metric-schemas-change').textContent = '등록된 스키마';

        document.getElementById('metric-prod-topics').textContent = prodTopics;
        const prodPercent = totalTopics > 0 ? Math.round((prodTopics / totalTopics) * 100) : 0;
        document.getElementById('metric-prod-percent').textContent = `${prodPercent}% of total`;

        document.getElementById('metric-total-teams').textContent = teams.length;
        document.getElementById('metric-teams-info').textContent = '관리 중인 팀';

        document.getElementById('metric-total-tags').textContent = tags.length;
        document.getElementById('metric-tags-info').textContent = '사용 중인 태그';
    }

    renderEnvDistribution(topics) {
        const envStats = topics.reduce((acc, topic) => {
            const env = topic.environment || 'unknown';
            if (!acc[env]) acc[env] = { count: 0, partitions: 0 };
            acc[env].count += 1;
            acc[env].partitions += topic.partition_count || 0;
            return acc;
        }, {});

        const maxPartitions = Math.max(...Object.values(envStats).map(s => s.partitions), 1);
        const container = document.getElementById('env-distribution-chart');
        
        const html = `
            <div class="env-bar-chart">
                ${['prod', 'stg', 'dev'].map(env => {
                    const stat = envStats[env] || { count: 0, partitions: 0 };
                    const width = Math.max((stat.partitions / maxPartitions) * 100, 5); // 최소 5%
                    const showText = width > 20; // 20% 이상일 때만 내부 텍스트
                    return `
                        <div class="env-bar-item">
                            <div class="env-bar-label">${env.toUpperCase()}</div>
                            <div class="env-bar-track">
                                <div class="env-bar-fill ${env}" style="width: ${width}%">
                                    ${showText ? `${stat.count} topics • ${stat.partitions} partitions` : ''}
                                </div>
                                ${!showText && stat.count > 0 ? `<span style="position: absolute; right: 10px; top: 50%; transform: translateY(-50%); font-size: 0.75rem; color: var(--text-muted);">${stat.count} topics • ${stat.partitions} partitions</span>` : ''}
                            </div>
                        </div>
                    `;
                }).join('')}
            </div>
        `;
        
        container.innerHTML = html;
    }

    /**
     * Kafka 클러스터 상태 렌더링
     */
    renderClusterStatus(clusterStatus) {
        const container = document.getElementById('cluster-status-info');
        
        if (!clusterStatus) {
            container.innerHTML = '<p style="text-align: center; color: var(--text-muted);">Cannot load cluster status.</p>';
            return;
        }

        const brokers = clusterStatus.brokers || [];
        const controllerBroker = brokers.find(b => b.is_controller);
        
        const html = `
            <div class="cluster-summary">
                <div class="cluster-stat">
                    <div class="stat-label">Controller</div>
                    <div class="stat-value">Broker ${clusterStatus.controller_id || 'N/A'}</div>
                    <div class="stat-detail">${controllerBroker ? `${controllerBroker.host}:${controllerBroker.port}` : ''}</div>
                </div>
                <div class="cluster-stat">
                    <div class="stat-label">Brokers</div>
                    <div class="stat-value">${brokers.length}</div>
                </div>
                <div class="cluster-stat">
                    <div class="stat-label">Total Topics</div>
                    <div class="stat-value">${clusterStatus.total_topics || 0}</div>
                </div>
                <div class="cluster-stat">
                    <div class="stat-label">Total Partitions</div>
                    <div class="stat-value">${clusterStatus.total_partitions || 0}</div>
                </div>
            </div>
            
            <div class="broker-grid">
                ${brokers.map(broker => `
                    <div class="broker-card ${broker.is_controller ? 'controller' : ''}" data-broker-id="${broker.broker_id}">
                        <div class="broker-header">
                            <strong>Broker ${broker.broker_id}</strong>
                            ${broker.is_controller ? '<span class="badge badge-primary">CONTROLLER</span>' : ''}
                        </div>
                        <div class="broker-info">
                            <div class="broker-host">${broker.host}:${broker.port}</div>
                            <div class="broker-partitions">
                                <i class="fas fa-layer-group"></i> ${broker.leader_partition_count || 0} leader partitions
                            </div>
                        </div>
                    </div>
                `).join('')}
            </div>
        `;

        container.innerHTML = html;
    }

    renderRecentActivitiesList(activities) {
        const container = document.getElementById('recent-activities-list');
        
        if (!activities || activities.length === 0) {
            container.innerHTML = '<p style="text-align: center; color: var(--text-muted);">활동이 없습니다.</p>';
            return;
        }

        const html = activities.map(activity => {
            // 날짜 파싱 개선
            let timeStr = '최근';
            try {
                const date = new Date(activity.occurred_at);
                if (!isNaN(date.getTime())) {
                    timeStr = date.toLocaleString('ko-KR', {
                        month: 'short',
                        day: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit'
                    });
                }
            } catch (e) {
                console.warn('날짜 파싱 실패:', activity.occurred_at);
            }

            const actionText = activity.action || 'ACTION';
            const targetName = activity.target_name || 'unknown';
            
            return `
                <div style="padding: 0.75rem 0; border-bottom: 1px solid var(--border-color);">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 0.25rem;">
                        <span style="font-weight: 500; font-size: 0.875rem;">${actionText} - ${targetName}</span>
                        <span style="font-size: 0.75rem; color: var(--text-muted);">${timeStr}</span>
                    </div>
                    <div style="font-size: 0.75rem; color: var(--text-muted);">
                        ${activity.actor || 'System'}
                    </div>
                </div>
            `;
        }).join('');

        container.innerHTML = html;
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
            const teamFilter = document.getElementById('topic-team-filter')?.value ?? '';
            const tagFilter = document.getElementById('topic-tag-filter')?.value ?? '';

            // 실제 토픽 목록 조회
            const topicsData = await api.getTopics();
            console.log('토픽 API 응답:', topicsData);
            
            const topics = topicsData.topics || [];
            console.log(`총 ${topics.length}개 토픽 로드됨`);

            // 토픽 데이터 매핑
            const mapped = topics.map(topic => {
                console.log('토픽 매핑:', topic.name, '태그:', topic.tags);
                return {
                    topic_name: topic.name,
                    owner: topic.owner,
                    doc: topic.doc,
                    tags: topic.tags || [],
                    partition_count: topic.partition_count,
                    replication_factor: topic.replication_factor,
                    environment: topic.environment,
                };
            });

            // 팀 및 태그 필터 옵션 업데이트
            this.updateFilterOptions(mapped);

            const filtered = mapped.filter((item) => {
                const envMatches = !envFilter || item.environment === envFilter;
                const sf = (searchFilter || '').toLowerCase();
                const searchMatches = !sf || item.topic_name.toLowerCase().includes(sf);
                const teamMatches = !teamFilter || item.owner === teamFilter;
                const tagMatches = !tagFilter || (item.tags && item.tags.includes(tagFilter));
                return envMatches && searchMatches && teamMatches && tagMatches;
            });

            console.log(`필터링 후 ${filtered.length}개 토픽 표시`);
            TableRenderer.renderTopicsTable(filtered);
        } catch (error) {
            console.error('토픽 로드 실패:', error);
            Toast.error(`토픽 목록 조회 실패: ${error.message}`);
        } finally {
            Loading.hide();
        }
    }

    /**
     * 팀 및 태그 필터 옵션 업데이트
     */
    updateFilterOptions(topics) {
        // 고유한 팀 목록 추출
        const teams = [...new Set(topics.map(t => t.owner).filter(o => o))];
        const teamFilter = document.getElementById('topic-team-filter');
        if (teamFilter) {
            const currentValue = teamFilter.value;
            teamFilter.innerHTML = '<option value="">전체 팀</option>';
            teams.sort().forEach(team => {
                teamFilter.innerHTML += `<option value="${team}">${team}</option>`;
            });
            teamFilter.value = currentValue; // 선택 상태 유지
        }

        // 고유한 태그 목록 추출
        const tags = [...new Set(topics.flatMap(t => t.tags || []))];
        const tagFilter = document.getElementById('topic-tag-filter');
        if (tagFilter) {
            const currentValue = tagFilter.value;
            tagFilter.innerHTML = '<option value="">전체 태그</option>';
            tags.sort().forEach(tag => {
                tagFilter.innerHTML += `<option value="${tag}">${tag}</option>`;
            });
            tagFilter.value = currentValue; // 선택 상태 유지
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
                        compatibility_mode: artifact.compatibility_mode || null,
                        owner: artifact.owner || null,
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
                compatibility_mode: group.compatibility_mode,
                owner: group.owner,
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
     * 팀별 분석 로드
     */
    async loadAnalytics() {
        try {
            Loading.show();

            // 토픽 및 활동 데이터 가져오기
            const [topicsData, activities] = await Promise.all([
                api.getTopics(),
                api.getActivityHistory({ limit: 100 }).catch(() => [])
            ]);

            const topics = topicsData.topics || [];
            
            // 팀 목록 추출
            const teams = [...new Set(topics.map(t => t.owner).filter(o => o))].sort();
            const teamFilter = document.getElementById('analytics-team-filter');
            if (teamFilter) {
                teamFilter.innerHTML = '<option value="">전체 팀</option>';
                teams.forEach(team => {
                    teamFilter.innerHTML += `<option value="${team}">${team}</option>`;
                });
            }

            // 팀 필터 변경 이벤트
            document.getElementById('analytics-team-filter')?.addEventListener('change', () => {
                this.renderTeamAnalytics(topics, activities);
            });

            // 초기 렌더링
            this.renderTeamAnalytics(topics, activities);

        } catch (error) {
            console.error('팀별 분석 로드 실패:', error);
            Toast.error(`팀별 분석 조회 실패: ${error.message}`);
        } finally {
            Loading.hide();
        }
    }

    /**
     * 팀별 분석 렌더링
     */
    renderTeamAnalytics(topics, activities) {
        const selectedTeam = document.getElementById('analytics-team-filter')?.value || '';
        
        // 필터링
        const filteredTopics = selectedTeam 
            ? topics.filter(t => t.owner === selectedTeam)
            : topics;

        // 메트릭 계산
        const totalTopics = filteredTopics.length;
        const envDistribution = filteredTopics.reduce((acc, t) => {
            acc[t.environment] = (acc[t.environment] || 0) + 1;
            return acc;
        }, {});
        
        const avgPartitions = totalTopics > 0
            ? Math.round(filteredTopics.reduce((sum, t) => sum + (t.partition_count || 0), 0) / totalTopics)
            : 0;

        // 최근 7일 활동 필터링 (팀도 필터링)
        const sevenDaysAgo = new Date();
        sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);
        const recentActivities = activities.filter(a => {
            const activityDate = new Date(a.timestamp);
            const isRecent = activityDate >= sevenDaysAgo;
            const isTeamMatch = !selectedTeam || a.team === selectedTeam;
            return isRecent && isTeamMatch;
        });

        // 메트릭 업데이트
        document.getElementById('team-total-topics').textContent = totalTopics;
        document.getElementById('team-topics-change').textContent = selectedTeam || '전체';

        const envText = Object.entries(envDistribution)
            .map(([env, count]) => `${env.toUpperCase()}: ${count}`)
            .join(' / ') || '-';
        document.getElementById('team-env-distribution').textContent = Object.keys(envDistribution).length;
        document.getElementById('team-env-info').textContent = envText;

        document.getElementById('team-avg-partitions').textContent = avgPartitions;
        document.getElementById('team-partitions-info').textContent = `${totalTopics}개 토픽 평균`;

        document.getElementById('team-recent-activities').textContent = recentActivities.length;
        document.getElementById('team-activities-info').textContent = '최근 7일';

        // 환경별 분포 차트
        this.renderTeamEnvChart(envDistribution);

        // 활동 차트
        this.renderTeamActivityChart(recentActivities);

        // 토픽 테이블
        this.renderTeamTopicsTable(filteredTopics);
    }

    /**
     * 팀별 환경 분포 차트 렌더링
     */
    renderTeamEnvChart(envDistribution) {
        const container = document.getElementById('team-env-chart');
        const maxCount = Math.max(...Object.values(envDistribution), 1);
        
        const html = `
            <div class="env-bar-chart">
                ${['prod', 'stg', 'dev'].map(env => {
                    const count = envDistribution[env] || 0;
                    const width = Math.max((count / maxCount) * 100, 5);
                    return `
                        <div class="env-bar-item">
                            <div class="env-bar-label">${env.toUpperCase()}</div>
                            <div class="env-bar-track">
                                <div class="env-bar-fill ${env}" style="width: ${width}%">
                                    ${width > 20 ? `${count}개` : ''}
                                </div>
                                ${width <= 20 && count > 0 ? `<span style="margin-left: 10px;">${count}개</span>` : ''}
                            </div>
                        </div>
                    `;
                }).join('')}
            </div>
        `;
        
        container.innerHTML = html || '<p style="text-align: center; color: var(--text-muted);">데이터가 없습니다.</p>';
    }

    /**
     * 팀별 활동 차트 렌더링
     */
    renderTeamActivityChart(activities) {
        const container = document.getElementById('team-activity-chart');
        
        // 액션별 그룹화
        const actionCounts = activities.reduce((acc, a) => {
            const action = a.action || 'UNKNOWN';
            acc[action] = (acc[action] || 0) + 1;
            return acc;
        }, {});

        const maxCount = Math.max(...Object.values(actionCounts), 1);
        
        const html = `
            <div class="env-bar-chart">
                ${Object.entries(actionCounts).map(([action, count]) => {
                    const width = Math.max((count / maxCount) * 100, 5);
                    // 바가 충분히 클 때만 (30% 이상) 바 안에 텍스트 표시
                    return `
                        <div class="env-bar-item">
                            <div class="env-bar-label">${action}</div>
                            <div class="env-bar-track">
                                <div class="env-bar-fill" style="width: ${width}%; background-color: var(--primary-color);">
                                    ${width > 30 ? `${count}건` : ''}
                                </div>
                                ${width <= 30 ? `<span style="margin-left: 8px; font-size: 0.875rem;">${count}건</span>` : ''}
                            </div>
                        </div>
                    `;
                }).join('')}
            </div>
        `;
        
        container.innerHTML = html || '<p style="text-align: center; color: var(--text-muted);">활동이 없습니다.</p>';
    }

    /**
     * 팀별 토픽 테이블 렌더링
     */
    renderTeamTopicsTable(topics) {
        const tbody = document.getElementById('team-topics-table-body');
        
        if (!topics || topics.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="6" style="text-align: center; padding: 2rem; color: var(--text-muted);">
                        토픽이 없습니다.
                    </td>
                </tr>
            `;
            return;
        }

        tbody.innerHTML = topics.map(topic => {
            const tags = topic.tags && topic.tags.length > 0 
                ? topic.tags.map(tag => {
                    const colorClass = TableRenderer.getTagColorClass(tag);
                    return `<span class="tag-badge ${colorClass}">${TableRenderer.escapeHtml(tag)}</span>`;
                  }).join(' ')
                : '<span style="color: var(--text-muted);">-</span>';

            const docHtml = topic.doc 
                ? `<a href="${TableRenderer.escapeHtml(topic.doc)}" target="_blank" rel="noopener noreferrer" title="문서 보기" style="color: var(--primary);">
                    <i class="fas fa-external-link-alt"></i>
                   </a>`
                : '<span style="color: var(--text-muted);">-</span>';

            return `
                <tr>
                    <td><div style="font-weight: 500;">${TableRenderer.escapeHtml(topic.name)}</div></td>
                    <td><span class="status-badge ${TableRenderer.getEnvClass(topic.environment)}">${TableRenderer.escapeHtml(topic.environment.toUpperCase())}</span></td>
                    <td style="text-align: center;">${topic.partition_count || '-'}</td>
                    <td style="text-align: center;">${topic.replication_factor || '-'}</td>
                    <td>${tags}</td>
                    <td style="text-align: center;">${docHtml}</td>
                </tr>
            `;
        }).join('');
    }

    /**
     * 활동 히스토리 로드
     */
    async loadHistory() {
        try {
            Loading.show();

            // 팀 필터 초기화 (첫 로드 시에만)
            const teamFilter = document.getElementById('history-team-filter');
            if (teamFilter && teamFilter.options.length === 1) {
                const topicsData = await api.getTopics().catch(() => ({ topics: [] }));
                const teams = [...new Set(topicsData.topics.map(t => t.owner).filter(o => o))].sort();
                teams.forEach(team => {
                    const option = document.createElement('option');
                    option.value = team;
                    option.textContent = team;
                    teamFilter.appendChild(option);
                });
            }

            const fromDate = document.getElementById('history-from-date')?.value;
            const toDate = document.getElementById('history-to-date')?.value;
            const activityType = document.getElementById('history-type-filter')?.value;
            const action = document.getElementById('history-action-filter')?.value;
            const team = document.getElementById('history-team-filter')?.value;
            const actor = document.getElementById('history-actor-filter')?.value;

            const filters = {
                from_date: fromDate || undefined,
                to_date: toDate || undefined,
                activity_type: activityType || undefined,
                action: action || undefined,
                team: team || undefined,
                actor: actor || undefined,
                limit: 100
            };

            const activities = await api.getActivityHistory(filters);
            
            TableRenderer.renderHistoryTable(activities);
        } catch (error) {
            console.error('히스토리 로드 실패:', error);
            Toast.error(`활동 히스토리 조회 실패: ${error.message}`);
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
            
            // 대시보드 카운터 업데이트
            try {
                const schemaCount = await api.getSchemaCount();
                const schemaCountEl = document.getElementById('schema-count');
                if (schemaCountEl) {
                    schemaCountEl.textContent = schemaCount.count;
                }
            } catch (err) {
                console.error('스키마 카운트 업데이스트 실패:', err);
            }
            Toast.success(
                `스키마 동기화 완료! 총 ${result.total}개 (새로 추가: ${result.added}개, 업데이트: ${result.updated}개)`
            );
            
            // 대시보드 최근 활동 갱신
            try {
                const activities = await api.getRecentActivities(10);
                ActivityRenderer.renderRecentActivities(activities);
            } catch (error) {
                console.error('최근 활동 갱신 실패:', error);
            }
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

            // 환경 선택 검증
            if (!formData['single-topic-env']) {
                Toast.error('환경을 선택해주세요.');
                return;
            }

            // 토픽 이름 검증
            const topicName = formData['single-topic-name'];
            if (!topicName) {
                Toast.error('토픽명을 입력해주세요.');
                return;
            }
            const topicNamePattern = /^[a-z0-9._-]+$/;
            if (!topicNamePattern.test(topicName)) {
                Toast.error('토픽 이름 형식이 올바르지 않습니다. 형식: 소문자, 숫자, ., _, - 만 사용 가능');
                return;
            }

            // Metadata 객체 구성
            const metadata = {
                owner: formData['single-topic-owner'],
                doc: formData['single-topic-doc'] || 'https://wiki.example.com',
                tags: formData['single-topic-tags'] ? 
                    formData['single-topic-tags'].split(',').map(t => t.trim()).filter(t => t) : []
            };

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
                    metadata: metadata
                }]
            };

            // 디버깅: 전송할 데이터 확인
            console.log('=== 토픽 생성 요청 데이터 ===');
            console.log('Full batch:', JSON.stringify(batch, null, 2));
            console.log('Form data:', formData);
            console.log('Metadata:', metadata);

            // 바로 Apply 실행
            const result = await api.topicBatchApply(batch);
            
            Toast.success('토픽이 성공적으로 생성되었습니다!');
            Modal.hide('create-single-topic-modal');
            form.reset();
            
            // 토픽 목록 새로고침
            if (this.currentTab === 'topics') {
                await this.loadTopics();
            }
            
            // 대시보드 최근 활동 갱신
            try {
                const activities = await api.getRecentActivities(10);
                ActivityRenderer.renderRecentActivities(activities);
                console.log('토픽 생성 후 최근 활동 갱신 완료');
            } catch (error) {
                console.error('최근 활동 갱신 실패:', error);
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
     * YAML 파일 업로드 처리 (백엔드로 전송 및 Dry-Run)
     */
    async handleYAMLFileUpload(event) {
        const file = event.target.files[0];
        if (!file) return;

        try {
            Loading.show();
            
            // 백엔드로 YAML 파일 전송 (파싱 및 Dry-Run)
            const result = await api.topicBatchUpload(file);
            
            // Dry-Run 결과 파싱
            const totalItems = result.summary?.total_items || 0;
            const createCount = result.summary?.create_count || 0;
            const alterCount = result.summary?.alter_count || 0;
            const deleteCount = result.summary?.delete_count || 0;
            const violationCount = result.summary?.violation_count || 0;
            const errorCount = result.violations?.filter(v => v.severity === 'error').length || 0;
            const warningCount = violationCount - errorCount;
            
            // 토픽 액션별 그룹화
            const createTopics = result.plan?.filter(p => p.action === 'CREATE') || [];
            const alterTopics = result.plan?.filter(p => p.action === 'ALTER') || [];
            const deleteTopics = result.plan?.filter(p => p.action === 'DELETE') || [];
            
            // 결과 표시
            const summary = `
                <div class="dry-run-result">
                    <h4 style="margin-bottom: 16px; color: #2c3e50;">📋 파싱 결과 미리보기</h4>
                    
                    <!-- 요약 통계 -->
                    <div class="summary-cards" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 12px; margin-bottom: 20px;">
                        <div style="padding: 12px; background: #e8f5e9; border-radius: 6px; text-align: center;">
                            <div style="font-size: 24px; font-weight: bold; color: #2e7d32;">${createCount}</div>
                            <div style="font-size: 12px; color: #558b2f; margin-top: 4px;">생성</div>
                        </div>
                        <div style="padding: 12px; background: #fff3e0; border-radius: 6px; text-align: center;">
                            <div style="font-size: 24px; font-weight: bold; color: #f57c00;">${alterCount}</div>
                            <div style="font-size: 12px; color: #ef6c00; margin-top: 4px;">수정</div>
                        </div>
                        <div style="padding: 12px; background: #ffebee; border-radius: 6px; text-align: center;">
                            <div style="font-size: 24px; font-weight: bold; color: #c62828;">${deleteCount}</div>
                            <div style="font-size: 12px; color: #b71c1c; margin-top: 4px;">삭제</div>
                        </div>
                        <div style="padding: 12px; background: ${errorCount > 0 ? '#ffebee' : '#f5f5f5'}; border-radius: 6px; text-align: center;">
                            <div style="font-size: 24px; font-weight: bold; color: ${errorCount > 0 ? '#c62828' : '#757575'};">${errorCount}</div>
                            <div style="font-size: 12px; color: ${errorCount > 0 ? '#b71c1c' : '#9e9e9e'}; margin-top: 4px;">에러</div>
                        </div>
                    </div>

                    ${this.renderTopicActionSection('생성', 'CREATE', createTopics, '#4caf50')}
                    ${this.renderTopicActionSection('수정', 'ALTER', alterTopics, '#ff9800')}
                    ${this.renderTopicActionSection('삭제', 'DELETE', deleteTopics, '#f44336')}
                    
                    ${result.violations && result.violations.length > 0 ? `
                        <div class="violations-section" style="margin-top: 20px;">
                            <div style="display: flex; align-items: center; justify-content: space-between; padding: 12px; background: #fff8e1; border-left: 4px solid #ffa726; border-radius: 4px; cursor: pointer;" onclick="this.nextElementSibling.style.display = this.nextElementSibling.style.display === 'none' ? 'block' : 'none'">
                                <strong style="color: #f57c00;">⚠️ 정책 위반 상세 (${violationCount}개)</strong>
                                <span style="color: #ef6c00; font-size: 12px;">클릭하여 펼치기/접기</span>
                            </div>
                            <div style="display: none; margin-top: 12px; max-height: 300px; overflow-y: auto;">
                                ${result.violations.map(v => `
                                    <div style="margin-bottom: 10px; padding: 10px; background: ${v.severity === 'error' ? '#ffebee' : '#fff3cd'}; border-left: 3px solid ${v.severity === 'error' ? '#e53935' : '#ffa726'}; border-radius: 4px;">
                                        <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px;">
                                            <span style="font-size: 11px; padding: 2px 6px; background: ${v.severity === 'error' ? '#e53935' : '#ffa726'}; color: white; border-radius: 3px; font-weight: bold;">
                                                ${v.severity.toUpperCase()}
                                            </span>
                                            <strong style="color: #37474f; font-size: 13px;">${v.name}</strong>
                                        </div>
                                        <div style="font-size: 12px; color: #546e7a; margin-left: 4px;">${v.message}</div>
                                        ${v.rule ? `<div style="font-size: 11px; color: #78909c; margin-top: 4px; margin-left: 4px;">규칙: ${v.rule}</div>` : ''}
                                    </div>
                                `).join('')}
                            </div>
                        </div>
                    ` : ''}
                    
                    <div style="margin-top: 20px; padding: 14px; background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%); border-radius: 6px; border-left: 4px solid #1976d2;">
                        <div style="display: flex; align-items: center; gap: 8px;">
                            <strong style="color: #0d47a1; font-size: 14px;">📌 다음 단계</strong>
                        </div>
                        <p style="margin: 8px 0 0; color: #1565c0; font-size: 13px; line-height: 1.5;">
                            결과를 확인한 후 "2. 적용" 탭에서 실제 적용을 진행하세요.
                        </p>
                    </div>
                </div>
            `;
            
            document.getElementById('yaml-preview').style.display = 'block';
            document.getElementById('yaml-preview-content').innerHTML = summary;
            
            if (errorCount > 0) {
                // 에러 상세 내역을 포함한 메시지
                const errorDetails = result.violations
                    ?.filter(v => v.severity === 'error')
                    .map(v => `• ${v.name}: ${v.message}`)
                    .join('\n') || '';
                
                console.error('정책 위반 발견:', errorDetails);
                
                Toast.error(
                    `정책 위반 발견! ${errorCount}개의 에러로 인해 적용할 수 없습니다.\n\n${errorDetails.substring(0, 200)}...`
                );
                
                // Dry-Run 결과는 표시
                document.getElementById('yaml-preview').style.display = 'block';
                document.getElementById('yaml-preview-content').innerHTML = summary;
            } else {
                // YAML 파일 내용을 읽어서 원본 요청 데이터 생성
                const fileContent = await file.text();
                const yaml = jsyaml.load(fileContent);
                
                // Apply 요청 형식으로 저장 (원본 YAML 데이터)
                this.currentBatchRequest = {
                    kind: yaml.kind,
                    env: yaml.env,
                    change_id: yaml.change_id,
                    items: yaml.items
                };
                this.currentBatchResult = this.currentBatchRequest;  // Apply API용
                this.currentBatchPlan = result;  // Dry-Run 결과 (표시용)
                
                Toast.success(`YAML 파싱 완료! ${totalItems}개 토픽 준비됨.`);
                
                // 배치 모달 열고 적용 탭으로 전환
                Modal.show('batch-topic-modal');
                this.switchBatchTab('apply');
                
                // 적용 탭에 결과 표시
                const planResults = document.getElementById('plan-results');
                if (planResults) {
                    planResults.innerHTML = summary;
                }
                document.getElementById('apply-batch').style.display = 'block';
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
     * 토픽 액션 섹션 렌더링 (생성/수정/삭제)
     */
    renderTopicActionSection(actionName, actionType, topics, borderColor) {
        if (!topics || topics.length === 0) {
            return '';
        }

        const sectionId = `section-${actionType.toLowerCase()}`;
        const iconMap = {
            'CREATE': '➕',
            'ALTER': '✏️',
            'DELETE': '🗑️'
        };

        return `
            <div class="topic-action-section" style="margin-bottom: 16px;">
                <div style="display: flex; align-items: center; justify-content: space-between; padding: 10px 12px; background: ${borderColor}15; border-left: 4px solid ${borderColor}; border-radius: 4px; cursor: pointer;" onclick="document.getElementById('${sectionId}').style.display = document.getElementById('${sectionId}').style.display === 'none' ? 'block' : 'none'">
                    <strong style="color: ${borderColor}; font-size: 14px;">
                        ${iconMap[actionType]} ${actionName}된 토픽 (${topics.length}개)
                    </strong>
                    <span style="color: ${borderColor}; font-size: 11px;">클릭하여 펼치기/접기</span>
                </div>
                <div id="${sectionId}" style="display: ${topics.length <= 5 ? 'block' : 'none'}; margin-top: 8px; max-height: 400px; overflow-y: auto;">
                    ${topics.map(topic => this.renderTopicItem(topic, actionType, borderColor)).join('')}
                </div>
            </div>
        `;
    }

    /**
     * 개별 토픽 아이템 렌더링
     */
    renderTopicItem(topic, actionType, borderColor) {
        const hasChanges = topic.diff && Object.keys(topic.diff).length > 0;
        
        return `
            <div style="margin-bottom: 8px; padding: 10px; background: #fafafa; border: 1px solid #e0e0e0; border-radius: 4px;">
                <div style="display: flex; align-items: center; gap: 8px; margin-bottom: ${hasChanges ? '8px' : '0'};">
                    <code style="font-size: 13px; color: #37474f; font-weight: 500;">${topic.name}</code>
                    <span style="font-size: 10px; padding: 2px 6px; background: ${borderColor}; color: white; border-radius: 3px; font-weight: bold;">
                        ${actionType}
                    </span>
                </div>
                ${hasChanges ? `
                    <div style="margin-top: 8px; padding: 8px; background: white; border-radius: 3px; border: 1px solid #e0e0e0;">
                        <div style="font-size: 11px; color: #78909c; margin-bottom: 6px; font-weight: 500;">📝 변경 사항:</div>
                        ${Object.entries(topic.diff).map(([key, value]) => `
                            <div style="margin-bottom: 4px; padding: 4px 6px; background: #f5f5f5; border-radius: 3px; font-size: 11px;">
                                <span style="color: #546e7a; font-weight: 500;">${this.formatConfigKey(key)}:</span>
                                <span style="color: #f57c00; margin-left: 4px;">${value}</span>
                            </div>
                        `).join('')}
                    </div>
                ` : ''}
                ${topic.target_config && actionType === 'CREATE' ? `
                    <div style="margin-top: 8px; padding: 8px; background: white; border-radius: 3px; border: 1px solid #e0e0e0;">
                        <div style="font-size: 11px; color: #78909c; margin-bottom: 6px; font-weight: 500;">⚙️ 설정:</div>
                        ${this.renderTopicConfig(topic.target_config)}
                    </div>
                ` : ''}
            </div>
        `;
    }

    /**
     * 토픽 설정 렌더링 (CREATE 시)
     */
    renderTopicConfig(config) {
        const importantKeys = ['partitions', 'replication_factor', 'retention_ms', 'retention_bytes'];
        const filtered = Object.entries(config)
            .filter(([key]) => importantKeys.includes(key))
            .map(([key, value]) => `
                <span style="font-size: 11px; color: #546e7a; margin-right: 12px;">
                    <strong>${this.formatConfigKey(key)}:</strong> ${this.formatConfigValue(value)}
                </span>
            `).join('');
        
        return filtered || '<span style="font-size: 11px; color: #9e9e9e;">기본 설정</span>';
    }

    /**
     * 설정 키 포맷팅
     */
    formatConfigKey(key) {
        const keyMap = {
            'partitions': '파티션',
            'replication_factor': '복제계수',
            'retention_ms': '보관기간',
            'retention_bytes': '보관용량',
            'min_insync_replicas': '최소동기복제',
            'cleanup_policy': '정리정책',
            'compression_type': '압축타입',
            'segment_ms': '세그먼트시간',
            'segment_bytes': '세그먼트크기'
        };
        return keyMap[key] || key;
    }

    /**
     * 설정 값 포맷팅
     */
    formatConfigValue(value) {
        if (typeof value === 'number') {
            // 시간 값 변환 (ms -> 일)
            if (value >= 86400000) {
                return `${(value / 86400000).toFixed(1)}일`;
            }
            // 용량 값 변환 (bytes -> GB/MB)
            if (value >= 1073741824) {
                return `${(value / 1073741824).toFixed(2)}GB`;
            }
            if (value >= 1048576) {
                return `${(value / 1048576).toFixed(2)}MB`;
            }
        }
        return value;
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
            const owner = document.getElementById('schema-owner')?.value;
            const compatibilityMode = document.getElementById('schema-compatibility-mode')?.value;

            if (!env || !changeId) {
                Toast.warning('환경과 변경 ID를 입력해주세요.');
                return;
            }

            if (!owner) {
                Toast.warning('소유 팀을 입력해주세요.');
                return;
            }

            const result = await api.uploadSchemaFiles({
                env,
                changeId,
                owner,
                files: this.selectedFiles,
                compatibilityMode: compatibilityMode || null,
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
                
                // 대시보드 카운터 업데이트 (모든 탭에서)
                try {
                    const schemaCount = await api.getSchemaCount();
                    const schemaCountEl = document.getElementById('schema-count');
                    if (schemaCountEl) {
                        schemaCountEl.textContent = schemaCount.count;
                    }
                } catch (err) {
                    console.error('스키마 카운트 업데이트 실패:', err);
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
        
        // 대시보드 최근 활동 갱신
        try {
            const activities = await api.getRecentActivities(10);
            ActivityRenderer.renderRecentActivities(activities);
            console.log('토픽 삭제 후 최근 활동 갱신 완료');
        } catch (error) {
            console.error('최근 활동 갱신 실패:', error);
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
