/**
 * Kafka Connect Manager UI
 * Modern, data-ops oriented dashboard
 */

class ConnectManager {
    constructor() {
        this.currentConnectId = null;
        this.connectors = [];
        this.tasks = [];
        this.plugins = [];
        this.autoRefreshInterval = null;
        this.currentSection = 'overview';
    }

    /**
     * 초기화
     */
    async init() {
        console.log('Connect Manager 초기화 시작...');
        
        // Connect ID 가져오기 (localStorage or settings)
        this.currentConnectId = localStorage.getItem('currentConnectId');
        
        console.log('Current Connect ID:', this.currentConnectId);
        
        // 이벤트 리스너 설정
        this.setupEventListeners();
        
        // Connect ID가 없으면 안내 메시지 표시
        if (!this.currentConnectId) {
            this.showNoConnectMessage();
            return;
        }
        
        // 초기 데이터 로드
        await this.loadOverviewData();
        
        // Auto-refresh 설정 (optional)
        this.setupAutoRefresh();
    }

    /**
     * Connect 미선택 메시지 표시
     */
    showNoConnectMessage() {
        const mainContent = document.querySelector('.main-content');
        if (mainContent) {
            mainContent.innerHTML = `
                <div style="display: flex; align-items: center; justify-content: center; height: 70vh;">
                    <div style="text-align: center; max-width: 600px; padding: 2rem;">
                        <i class="fas fa-plug" style="font-size: 4rem; color: var(--text-secondary); margin-bottom: 1.5rem;"></i>
                        <h2 style="margin-bottom: 1rem;">Kafka Connect가 선택되지 않았습니다</h2>
                        <p style="color: var(--text-secondary); margin-bottom: 2rem;">
                            Connect Manager를 사용하려면 먼저 설정 페이지에서 Kafka Connect를 선택해주세요.
                        </p>
                        <a href="/static/settings.html" class="btn btn-primary" style="display: inline-flex; align-items: center; gap: 0.5rem;">
                            <i class="fas fa-cog"></i>
                            설정 페이지로 이동
                        </a>
                    </div>
                </div>
            `;
        }
    }

    /**
     * 이벤트 리스너 설정
     */
    setupEventListeners() {
        // Sidebar navigation
        document.querySelectorAll('.sidebar-link').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const section = link.dataset.section;
                this.navigateToSection(section);
            });
        });

        // Theme toggle
        document.getElementById('theme-toggle')?.addEventListener('click', () => {
            this.toggleTheme();
        });

        // Auto-refresh toggle
        document.getElementById('auto-refresh-toggle')?.addEventListener('click', () => {
            this.toggleAutoRefresh();
        });

        // Search
        document.getElementById('global-search')?.addEventListener('input', (e) => {
            this.handleGlobalSearch(e.target.value);
        });

        // Connector filters
        document.getElementById('connector-search')?.addEventListener('input', (e) => {
            this.filterConnectors();
        });

        document.getElementById('connector-type-filter')?.addEventListener('change', () => {
            this.filterConnectors();
        });

        document.getElementById('connector-status-filter')?.addEventListener('change', () => {
            this.filterConnectors();
        });

        // Add Connector button
        document.getElementById('add-connector-btn')?.addEventListener('click', () => {
            this.showAddConnectorModal();
        });

        // Modal close buttons
        document.querySelectorAll('.modal-close').forEach(btn => {
            btn.addEventListener('click', () => {
                Modal.hideAll();
            });
        });

        // Modal background click
        document.querySelectorAll('.modal').forEach(modal => {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    Modal.hideAll();
                }
            });
        });

        // Refresh buttons
        document.getElementById('refresh-topology')?.addEventListener('click', () => {
            this.loadTopology();
        });
    }

    /**
     * 섹션 전환
     */
    navigateToSection(section) {
        // Update sidebar
        document.querySelectorAll('.sidebar-link').forEach(link => {
            link.classList.remove('active');
        });
        document.querySelector(`[data-section="${section}"]`)?.classList.add('active');

        // Update content
        document.querySelectorAll('.content-section').forEach(sec => {
            sec.classList.remove('active');
        });
        document.getElementById(`${section}-section`)?.classList.add('active');

        this.currentSection = section;

        // Load section data
        this.loadSectionData(section);
    }

    /**
     * 섹션별 데이터 로드
     */
    async loadSectionData(section) {
        switch (section) {
            case 'overview':
                await this.loadOverviewData();
                break;
            case 'connectors':
                await this.loadConnectorsData();
                break;
            case 'tasks':
                await this.loadTasksData();
                break;
            case 'plugins':
                await this.loadPluginsData();
                break;
            case 'workers':
                await this.loadWorkersData();
                break;
            case 'dlq':
                await this.loadDLQData();
                break;
            case 'settings':
                await this.loadSettingsData();
                break;
        }
    }

    /**
     * Overview 데이터 로드
     */
    async loadOverviewData() {
        try {
            console.log(`커넥터 목록 로드 중... (Connect ID: ${this.currentConnectId})`);
            
            // Load connectors with metadata
            const response = await api.get(`/v1/connect/${this.currentConnectId}/connectors?expand=status&expand=info`);
            
            console.log('커넥터 응답:', response);
            
            if (typeof response === 'object' && !Array.isArray(response)) {
                this.connectors = Object.entries(response).map(([name, info]) => ({
                    name,
                    ...info
                }));
            } else {
                this.connectors = response || [];
            }

            console.log(`로드된 커넥터 수: ${this.connectors.length}`);

            // Update metrics
            this.updateOverviewMetrics();
            
            // Render topology
            this.renderTopology();
            
            // Load charts (placeholder)
            this.renderCharts();
            
            if (this.connectors.length === 0) {
                this.showNoConnectorsMessage();
            }
        } catch (error) {
            console.error('Failed to load overview:', error);
            this.showErrorMessage(error.message);
        }
    }

    /**
     * 커넥터 없음 메시지
     */
    showNoConnectorsMessage() {
        const topologyView = document.getElementById('topology-view');
        if (topologyView) {
            topologyView.innerHTML = `
                <div style="text-align: center; padding: 2rem; color: var(--text-secondary);">
                    <i class="fas fa-inbox" style="font-size: 3rem; margin-bottom: 1rem; opacity: 0.5;"></i>
                    <p>등록된 커넥터가 없습니다.</p>
                    <p style="font-size: 0.875rem;">Connectors 섹션에서 새 커넥터를 추가해보세요.</p>
                </div>
            `;
        }
    }

    /**
     * 에러 메시지 표시
     */
    showErrorMessage(message) {
        const mainContent = document.querySelector('.main-content');
        if (mainContent) {
            const errorHtml = `
                <div style="display: flex; align-items: center; justify-content: center; height: 70vh;">
                    <div style="text-align: center; max-width: 600px; padding: 2rem;">
                        <i class="fas fa-exclamation-circle" style="font-size: 4rem; color: #EF4444; margin-bottom: 1.5rem;"></i>
                        <h2 style="margin-bottom: 1rem;">데이터를 불러올 수 없습니다</h2>
                        <p style="color: var(--text-secondary); margin-bottom: 1rem;">
                            ${message}
                        </p>
                        <p style="color: var(--text-secondary); font-size: 0.875rem; margin-bottom: 2rem;">
                            Connect 설정이 올바른지 확인하거나, 서버 로그를 확인해주세요.
                        </p>
                        <button class="btn btn-primary" onclick="location.reload()" style="display: inline-flex; align-items: center; gap: 0.5rem;">
                            <i class="fas fa-redo"></i>
                            다시 시도
                        </button>
                    </div>
                </div>
            `;
            
            // Overview 섹션에만 표시
            const overviewSection = document.getElementById('overview-section');
            if (overviewSection) {
                overviewSection.innerHTML = errorHtml;
            }
        }
        
        // Toast도 표시
        if (typeof Toast !== 'undefined') {
            Toast.error(`데이터 로드 실패: ${message}`);
        }
    }

    /**
     * Overview 메트릭 업데이트
     */
    updateOverviewMetrics() {
        const totalConnectors = this.connectors.length;
        const runningTasks = this.connectors.reduce((sum, conn) => {
            if (conn.status?.tasks) {
                return sum + conn.status.tasks.filter(t => t.state === 'RUNNING').length;
            }
            return sum;
        }, 0);
        const failedTasks = this.connectors.reduce((sum, conn) => {
            if (conn.status?.tasks) {
                return sum + conn.status.tasks.filter(t => t.state === 'FAILED').length;
            }
            return sum;
        }, 0);

        // Update DOM
        document.getElementById('total-connectors').textContent = totalConnectors;
        document.getElementById('running-tasks').textContent = runningTasks;
        document.getElementById('tasks-running').textContent = `${runningTasks} running`;
        document.getElementById('tasks-failed').textContent = `${failedTasks} failed`;
        
        // Health score (simple calculation)
        const healthScore = failedTasks === 0 ? 98 : Math.max(50, 98 - (failedTasks * 10));
        document.getElementById('health-score').textContent = healthScore;
    }

    /**
     * Topology 렌더링
     */
    renderTopology() {
        const topologyView = document.getElementById('topology-view');
        if (!topologyView) return;

        const sourceConnectors = this.connectors.filter(c => c.type === 'source');
        const sinkConnectors = this.connectors.filter(c => c.type === 'sink');

        topologyView.innerHTML = `
            <div class="topology-column">
                <h4>Source Connectors (${sourceConnectors.length})</h4>
                <div class="topology-items">
                    ${sourceConnectors.slice(0, 5).map(c => `
                        <div class="topology-item source">
                            <i class="fas fa-database"></i>
                            <span>${c.name}</span>
                        </div>
                    `).join('')}
                    ${sourceConnectors.length > 5 ? `<div class="topology-more">+${sourceConnectors.length - 5} more</div>` : ''}
                </div>
            </div>
            
            <div class="topology-column center">
                <h4>Topics</h4>
                <div class="topology-flow">
                    <i class="fas fa-arrow-right"></i>
                    <div class="topic-chip">kafka.topics</div>
                    <i class="fas fa-arrow-right"></i>
                </div>
            </div>
            
            <div class="topology-column">
                <h4>Sink Connectors (${sinkConnectors.length})</h4>
                <div class="topology-items">
                    ${sinkConnectors.slice(0, 5).map(c => `
                        <div class="topology-item sink">
                            <i class="fas fa-database"></i>
                            <span>${c.name}</span>
                        </div>
                    `).join('')}
                    ${sinkConnectors.length > 5 ? `<div class="topology-more">+${sinkConnectors.length - 5} more</div>` : ''}
                </div>
            </div>
        `;

        // Add inline styles for topology
        if (!document.getElementById('topology-styles')) {
            const style = document.createElement('style');
            style.id = 'topology-styles';
            style.textContent = `
                .topology-column { flex: 1; text-align: center; }
                .topology-column h4 { font-size: 0.875rem; margin-bottom: 1rem; color: var(--text-secondary); }
                .topology-items { display: flex; flex-direction: column; gap: 0.5rem; }
                .topology-item { padding: 0.5rem; background: var(--bg-hover); border-radius: var(--radius-md); display: flex; align-items: center; gap: 0.5rem; font-size: 0.75rem; }
                .topology-item.source { border-left: 3px solid var(--primary-blue); }
                .topology-item.sink { border-left: 3px solid var(--primary-teal); }
                .topology-flow { display: flex; align-items: center; justify-content: center; gap: 1rem; }
                .topic-chip { padding: 0.5rem 1rem; background: var(--bg-hover); border-radius: var(--radius-xl); font-size: 0.75rem; }
                .topology-more { font-size: 0.75rem; color: var(--text-secondary); padding: 0.5rem; }
            `;
            document.head.appendChild(style);
        }
    }

    /**
     * 차트 렌더링 (placeholder)
     */
    renderCharts() {
        // TODO: Chart.js 또는 다른 차트 라이브러리 사용
        console.log('Charts rendering - placeholder');
    }

    /**
     * Connectors 데이터 로드
     */
    async loadConnectorsData() {
        try {
            const response = await api.get(`/v1/connect/${this.currentConnectId}/connectors?expand=status&expand=info`);
            
            if (typeof response === 'object' && !Array.isArray(response)) {
                this.connectors = Object.entries(response).map(([name, info]) => ({
                    name,
                    ...info
                }));
            } else {
                this.connectors = response || [];
            }

            this.renderConnectorsTable();
        } catch (error) {
            console.error('Failed to load connectors:', error);
            Toast.error('커넥터 목록을 불러올 수 없습니다.');
        }
    }

    /**
     * Connectors 테이블 렌더링
     */
    renderConnectorsTable() {
        const tbody = document.getElementById('connectors-table-body');
        if (!tbody) return;

        if (this.connectors.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="8" style="text-align: center; padding: 2rem;">
                        커넥터가 없습니다.
                    </td>
                </tr>
            `;
            return;
        }

        tbody.innerHTML = this.connectors.map(conn => {
            const status = conn.status?.connector?.state || 'UNKNOWN';
            const tasks = conn.status?.tasks || [];
            const runningTasks = tasks.filter(t => t.state === 'RUNNING').length;
            const failedTasks = tasks.filter(t => t.state === 'FAILED').length;
            
            return `
                <tr>
                    <td>
                        <div class="connector-name">
                            <i class="fas fa-plug"></i>
                            ${conn.name}
                        </div>
                    </td>
                    <td>
                        <span class="badge badge-info">${conn.type || 'unknown'}</span>
                    </td>
                    <td>${conn.team || '-'}</td>
                    <td>
                        <div class="task-summary">
                            <span class="badge badge-success">${runningTasks}</span>
                            ${failedTasks > 0 ? `<span class="badge badge-danger">${failedTasks}</span>` : ''}
                        </div>
                    </td>
                    <td>
                        <span class="badge ${this.getStatusBadgeClass(status)}">${status}</span>
                    </td>
                    <td>${failedTasks}</td>
                    <td>-</td>
                    <td>
                        <div class="action-buttons">
                            ${status === 'RUNNING' ? 
                                `<button class="btn-icon" onclick="connectManager.pauseConnector('${conn.name}')" title="Pause">
                                    <i class="fas fa-pause"></i>
                                </button>` : 
                                `<button class="btn-icon" onclick="connectManager.resumeConnector('${conn.name}')" title="Resume">
                                    <i class="fas fa-play"></i>
                                </button>`
                            }
                            <button class="btn-icon" onclick="connectManager.restartConnector('${conn.name}')" title="Restart">
                                <i class="fas fa-redo"></i>
                            </button>
                            <button class="btn-icon" onclick="connectManager.deleteConnector('${conn.name}')" title="Delete">
                                <i class="fas fa-trash"></i>
                            </button>
                        </div>
                    </td>
                </tr>
            `;
        }).join('');

        // Add inline styles
        if (!document.getElementById('connector-table-styles')) {
            const style = document.createElement('style');
            style.id = 'connector-table-styles';
            style.textContent = `
                .connector-name { display: flex; align-items: center; gap: 0.5rem; font-weight: 500; }
                .task-summary { display: flex; gap: 0.375rem; }
                .action-buttons { display: flex; gap: 0.25rem; }
            `;
            document.head.appendChild(style);
        }
    }

    /**
     * Status 배지 클래스 가져오기
     */
    getStatusBadgeClass(status) {
        switch (status) {
            case 'RUNNING':
                return 'badge-success';
            case 'FAILED':
                return 'badge-danger';
            case 'PAUSED':
                return 'badge-warning';
            default:
                return 'badge-info';
        }
    }

    /**
     * Connector Actions
     */
    async pauseConnector(connectorName) {
        try {
            await api.put(`/v1/connect/${this.currentConnectId}/connectors/${connectorName}/pause`);
            Toast.success(`Connector "${connectorName}" paused`);
            await this.loadConnectorsData();
        } catch (error) {
            console.error('Failed to pause connector:', error);
            Toast.error('커넥터 일시정지에 실패했습니다.');
        }
    }

    async resumeConnector(connectorName) {
        try {
            await api.put(`/v1/connect/${this.currentConnectId}/connectors/${connectorName}/resume`);
            Toast.success(`Connector "${connectorName}" resumed`);
            await this.loadConnectorsData();
        } catch (error) {
            console.error('Failed to resume connector:', error);
            Toast.error('커넥터 재개에 실패했습니다.');
        }
    }

    async restartConnector(connectorName) {
        if (!confirm(`Restart connector "${connectorName}"?`)) return;
        
        try {
            await api.post(`/v1/connect/${this.currentConnectId}/connectors/${connectorName}/restart`);
            Toast.success(`Connector "${connectorName}" restarted`);
            await this.loadConnectorsData();
        } catch (error) {
            console.error('Failed to restart connector:', error);
            Toast.error('커넥터 재시작에 실패했습니다.');
        }
    }

    async deleteConnector(connectorName) {
        if (!confirm(`Delete connector "${connectorName}"? This action cannot be undone.`)) return;
        
        try {
            await api.delete(`/v1/connect/${this.currentConnectId}/connectors/${connectorName}`);
            Toast.success(`Connector "${connectorName}" deleted`);
            await this.loadConnectorsData();
        } catch (error) {
            console.error('Failed to delete connector:', error);
            Toast.error('커넥터 삭제에 실패했습니다.');
        }
    }

    /**
     * Tasks 데이터 로드
     */
    async loadTasksData() {
        // TODO: Implement tasks loading
        console.log('Loading tasks data...');
    }

    /**
     * Plugins 데이터 로드
     */
    async loadPluginsData() {
        try {
            this.plugins = await api.get(`/v1/connect/${this.currentConnectId}/connector-plugins`);
            this.renderPluginsGrid();
        } catch (error) {
            console.error('Failed to load plugins:', error);
            Toast.error('플러그인 목록을 불러올 수 없습니다.');
        }
    }

    /**
     * Plugins 그리드 렌더링
     */
    renderPluginsGrid() {
        const grid = document.getElementById('plugins-grid');
        if (!grid || !this.plugins) return;

        grid.innerHTML = this.plugins.map(plugin => {
            // API가 'class' 또는 'class_'로 올 수 있음
            const pluginClass = plugin.class || plugin.class_ || 'Unknown';
            const pluginType = plugin.type || 'unknown';
            const pluginVersion = plugin.version || 'N/A';
            
            return `
                <div class="plugin-card">
                    <div class="plugin-icon">
                        <i class="fas fa-puzzle-piece"></i>
                    </div>
                    <h4 title="${pluginClass}">${pluginClass}</h4>
                    <p class="plugin-type">${pluginType}</p>
                    <p class="plugin-version">${pluginVersion}</p>
                    <button class="btn btn-secondary btn-sm" onclick="connectManager.validatePlugin('${pluginClass}')">
                        Validate Config
                    </button>
                </div>
            `;
        }).join('');
    }

    /**
     * Workers 데이터 로드
     */
    async loadWorkersData() {
        // TODO: Implement workers loading
        console.log('Loading workers data...');
    }

    /**
     * DLQ 데이터 로드
     */
    async loadDLQData() {
        // TODO: Implement DLQ loading
        console.log('Loading DLQ data...');
    }

    /**
     * Settings 데이터 로드
     */
    async loadSettingsData() {
        // TODO: Implement settings loading
        console.log('Loading settings data...');
    }

    /**
     * Connector 필터링
     */
    filterConnectors() {
        const searchTerm = document.getElementById('connector-search')?.value.toLowerCase() || '';
        const typeFilter = document.getElementById('connector-type-filter')?.value || '';
        const statusFilter = document.getElementById('connector-status-filter')?.value || '';

        // TODO: Implement filtering logic
        console.log('Filtering:', { searchTerm, typeFilter, statusFilter });
    }

    /**
     * Theme 토글
     */
    toggleTheme() {
        document.body.classList.toggle('dark-theme');
        const isDark = document.body.classList.contains('dark-theme');
        localStorage.setItem('theme', isDark ? 'dark' : 'light');
        
        const icon = document.querySelector('#theme-toggle i');
        icon.className = isDark ? 'fas fa-moon' : 'fas fa-sun';
    }

    /**
     * Auto-refresh 토글
     */
    toggleAutoRefresh() {
        if (this.autoRefreshInterval) {
            clearInterval(this.autoRefreshInterval);
            this.autoRefreshInterval = null;
            Toast.info('Auto-refresh disabled');
        } else {
            this.setupAutoRefresh();
            Toast.info('Auto-refresh enabled (30s)');
        }
    }

    /**
     * Auto-refresh 설정
     */
    setupAutoRefresh() {
        // 30초마다 현재 섹션 데이터 새로고침
        this.autoRefreshInterval = setInterval(() => {
            this.loadSectionData(this.currentSection);
        }, 30000);
    }

    /**
     * 글로벌 검색
     */
    handleGlobalSearch(query) {
        // TODO: Implement global search
        console.log('Global search:', query);
    }

    /**
     * Add Connector 모달 표시
     */
    showAddConnectorModal() {
        // TODO: Implement modal
        Modal.show('add-connector-modal');
    }

    /**
     * Plugin 검증
     */
    async validatePlugin(pluginClass) {
        try {
            // 모달 열기 및 초기화
            const modalId = 'validate-config-modal';
            const pluginInput = document.getElementById('validate-plugin-class');
            const jsonTextarea = document.getElementById('validate-config-json');
            const resultPre = document.getElementById('validate-config-result');
            const runBtn = document.getElementById('validate-config-run-btn');

            if (!pluginInput || !jsonTextarea || !resultPre || !runBtn) {
                console.error('Validate modal elements not found');
                Toast.error('검증 모달 초기화에 실패했습니다.');
                return;
            }

            pluginInput.value = pluginClass;
            resultPre.textContent = '';

            // 기존 클릭 핸들러 제거 후 재바인딩 (중복 방지)
            const newRunBtn = runBtn.cloneNode(true);
            runBtn.parentNode.replaceChild(newRunBtn, runBtn);

            newRunBtn.addEventListener('click', async () => {
                // JSON 파싱
                let payload;
                try {
                    payload = JSON.parse(jsonTextarea.value);
                } catch (e) {
                    Toast.error('유효한 JSON을 입력하세요.');
                    resultPre.textContent = `JSON Parse Error: ${e.message}`;
                    return;
                }

                // Backend 호출
                try {
                    const endpoint = `/v1/connect/${this.currentConnectId}/connector-plugins/${encodeURIComponent(pluginClass)}/config/validate`;
                    const resp = await api.put(endpoint, payload);
                    resultPre.textContent = JSON.stringify(resp, null, 2);
                    Toast.success('검증이 완료되었습니다.');
                } catch (error) {
                    console.error('Validation failed:', error);
                    resultPre.textContent = `Validation Error:\n${error.message}`;
                    Toast.error('검증 요청에 실패했습니다.');
                }
            });

            // 모달 닫기 버튼 동작 보장
            document.querySelectorAll(`#${modalId} .modal-close`).forEach(btn => {
                btn.addEventListener('click', () => Modal.hide(modalId));
            });

            Modal.show(modalId);
        } catch (err) {
            console.error('Unexpected error in validatePlugin:', err);
            Toast.error('플러그인 검증 중 오류가 발생했습니다.');
        }
    }
}

// Global instance
const connectManager = new ConnectManager();

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    connectManager.init();
});
