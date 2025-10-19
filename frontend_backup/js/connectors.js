/**
 * Kafka Connect 관리 페이지 로직
 */

class ConnectorManager {
    constructor() {
        this.currentConnectId = null;
        this.connectors = [];
        this.filteredConnectors = [];
    }

    /**
     * 초기화
     */
    async init() {
        this.currentConnectId = api.currentConnectId;
        
        if (!this.currentConnectId) {
            this.showNoConnectMessage();
            return;
        }

        await this.loadCurrentConnectInfo();
        await this.loadConnectors();
        this.setupEventListeners();
    }

    /**
     * Connect 미선택 메시지 표시
     */
    showNoConnectMessage() {
        const infoDiv = document.getElementById('current-connect-info');
        if (infoDiv) {
            infoDiv.innerHTML = `
                <div class="alert alert-warning">
                    <i class="fas fa-exclamation-triangle"></i>
                    <strong>Connect가 선택되지 않았습니다.</strong>
                    <p>설정 페이지에서 Kafka Connect를 선택해주세요.</p>
                    <a href="/static/settings.html" class="btn btn-primary btn-sm">
                        <i class="fas fa-cog"></i> 설정으로 이동
                    </a>
                </div>
            `;
        }
    }

    /**
     * 현재 Connect 정보 로드
     */
    async loadCurrentConnectInfo() {
        try {
            const connect = await api.getKafkaConnect(this.currentConnectId);
            const infoDiv = document.getElementById('current-connect-info');
            
            infoDiv.innerHTML = `
                <div class="connect-info-grid">
                    <div class="info-item">
                        <span class="label"><i class="fas fa-tag"></i> Connect ID:</span>
                        <span class="value">${connect.connect_id}</span>
                    </div>
                    <div class="info-item">
                        <span class="label"><i class="fas fa-signature"></i> 이름:</span>
                        <span class="value">${connect.name}</span>
                    </div>
                    <div class="info-item">
                        <span class="label"><i class="fas fa-link"></i> URL:</span>
                        <span class="value"><code>${connect.url}</code></span>
                    </div>
                    <div class="info-item">
                        <span class="label"><i class="fas fa-server"></i> Cluster:</span>
                        <span class="value">${connect.cluster_id}</span>
                    </div>
                    <div class="info-item">
                        <span class="label"><i class="fas fa-circle"></i> 상태:</span>
                        <span class="badge ${connect.is_active ? 'badge-success' : 'badge-danger'}">
                            ${connect.is_active ? 'Active' : 'Inactive'}
                        </span>
                    </div>
                </div>
            `;
        } catch (error) {
            console.error('Connect 정보 로드 실패:', error);
            Toast.error('Connect 정보를 불러올 수 없습니다.');
        }
    }

    /**
     * 커넥터 목록 로드
     */
    async loadConnectors() {
        if (!this.currentConnectId) {
            return;
        }

        try {
            Loading.show();
            this.connectors = await api.getConnectors(this.currentConnectId);
            this.filteredConnectors = [...this.connectors];
            this.renderConnectors();
        } catch (error) {
            console.error('커넥터 목록 로드 실패:', error);
            Toast.error('커넥터 목록을 불러올 수 없습니다.');
            document.getElementById('connectors-list').innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-exclamation-circle"></i>
                    <p>커넥터 목록을 불러올 수 없습니다.</p>
                    <small>${error.message}</small>
                </div>
            `;
        } finally {
            Loading.hide();
        }
    }

    /**
     * 커넥터 목록 렌더링
     */
    renderConnectors() {
        const container = document.getElementById('connectors-list');
        
        if (!this.filteredConnectors || this.filteredConnectors.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-plug"></i>
                    <p>등록된 커넥터가 없습니다.</p>
                    <button class="btn btn-primary" id="create-first-connector-btn">
                        <i class="fas fa-plus"></i> 첫 커넥터 생성
                    </button>
                </div>
            `;
            
            document.getElementById('create-first-connector-btn')?.addEventListener('click', () => {
                this.openCreateModal();
            });
            return;
        }

        container.innerHTML = this.filteredConnectors.map(connector => `
            <div class="connector-card">
                <div class="connector-header">
                    <div class="connector-title">
                        <h4>${connector.name}</h4>
                        <span class="connector-type">${this.getConnectorType(connector.type)}</span>
                    </div>
                    <div class="connector-status">
                        ${this.renderStatusBadge(connector.state)}
                    </div>
                </div>
                <div class="connector-body">
                    <div class="connector-info">
                        <div class="info-row">
                            <span class="label">클래스:</span>
                            <span class="value"><code>${connector.connector.class}</code></span>
                        </div>
                        <div class="info-row">
                            <span class="label">태스크:</span>
                            <span class="value">${connector.tasks?.length || 0}개</span>
                        </div>
                        <div class="info-row">
                            <span class="label">토픽:</span>
                            <span class="value">${connector.topics?.join(', ') || '-'}</span>
                        </div>
                    </div>
                    <div class="connector-actions">
                        <button class="btn btn-sm btn-primary" onclick="connectorManager.viewDetails('${connector.name}')">
                            <i class="fas fa-info-circle"></i> 상세
                        </button>
                        ${this.renderControlButtons(connector)}
                        <button class="btn btn-sm btn-danger" onclick="connectorManager.deleteConnector('${connector.name}')">
                            <i class="fas fa-trash"></i> 삭제
                        </button>
                    </div>
                </div>
            </div>
        `).join('');
    }

    /**
     * 커넥터 타입 표시
     */
    getConnectorType(type) {
        return type === 'source' ? '📥 Source' : '📤 Sink';
    }

    /**
     * 상태 배지 렌더링
     */
    renderStatusBadge(state) {
        const stateMap = {
            'RUNNING': { class: 'success', icon: 'play', text: '실행 중' },
            'PAUSED': { class: 'warning', icon: 'pause', text: '일시정지' },
            'FAILED': { class: 'danger', icon: 'times', text: '실패' },
            'UNASSIGNED': { class: 'secondary', icon: 'question', text: '미할당' }
        };
        
        const status = stateMap[state] || { class: 'secondary', icon: 'question', text: state };
        
        return `
            <span class="badge badge-${status.class}">
                <i class="fas fa-${status.icon}"></i> ${status.text}
            </span>
        `;
    }

    /**
     * 제어 버튼 렌더링
     */
    renderControlButtons(connector) {
        if (connector.state === 'RUNNING') {
            return `
                <button class="btn btn-sm btn-warning" onclick="connectorManager.pauseConnector('${connector.name}')">
                    <i class="fas fa-pause"></i> 일시정지
                </button>
                <button class="btn btn-sm btn-secondary" onclick="connectorManager.restartConnector('${connector.name}')">
                    <i class="fas fa-redo"></i> 재시작
                </button>
            `;
        } else if (connector.state === 'PAUSED') {
            return `
                <button class="btn btn-sm btn-success" onclick="connectorManager.resumeConnector('${connector.name}')">
                    <i class="fas fa-play"></i> 재개
                </button>
                <button class="btn btn-sm btn-secondary" onclick="connectorManager.restartConnector('${connector.name}')">
                    <i class="fas fa-redo"></i> 재시작
                </button>
            `;
        } else {
            return `
                <button class="btn btn-sm btn-secondary" onclick="connectorManager.restartConnector('${connector.name}')">
                    <i class="fas fa-redo"></i> 재시작
                </button>
            `;
        }
    }

    /**
     * 이벤트 리스너 설정
     */
    setupEventListeners() {
        // 새로고침 버튼
        document.getElementById('refresh-connectors-btn')?.addEventListener('click', async () => {
            await this.loadConnectors();
            Toast.success('커넥터 목록을 새로고침했습니다.');
        });

        // 생성 버튼
        document.getElementById('create-connector-btn')?.addEventListener('click', () => {
            this.openCreateModal();
        });

        // 검색
        document.getElementById('connector-search')?.addEventListener('input', (e) => {
            this.filterConnectors(e.target.value);
        });

        // 상태 필터
        document.getElementById('connector-status-filter')?.addEventListener('change', (e) => {
            this.filterByStatus(e.target.value);
        });

        // 모달 닫기
        document.querySelectorAll('.modal-close').forEach(btn => {
            btn.addEventListener('click', () => {
                btn.closest('.modal').classList.remove('show');
            });
        });

        // 커넥터 생성 제출
        document.getElementById('submit-connector-btn')?.addEventListener('click', () => {
            this.submitConnector();
        });
    }

    /**
     * 커넥터 필터링 (검색)
     */
    filterConnectors(searchText) {
        const statusFilter = document.getElementById('connector-status-filter')?.value;
        
        this.filteredConnectors = this.connectors.filter(connector => {
            const matchesSearch = !searchText || 
                connector.name.toLowerCase().includes(searchText.toLowerCase()) ||
                connector.connector.class.toLowerCase().includes(searchText.toLowerCase());
            
            const matchesStatus = !statusFilter || connector.state === statusFilter;
            
            return matchesSearch && matchesStatus;
        });
        
        this.renderConnectors();
    }

    /**
     * 상태별 필터링
     */
    filterByStatus(status) {
        const searchText = document.getElementById('connector-search')?.value || '';
        this.filterConnectors(searchText);
    }

    /**
     * 생성 모달 열기
     */
    openCreateModal() {
        const modal = document.getElementById('create-connector-modal');
        modal.classList.add('show');
        
        // 폼 초기화
        document.getElementById('create-connector-form').reset();
    }

    /**
     * 커넥터 생성 제출
     */
    async submitConnector() {
        const name = document.getElementById('connector-name').value.trim();
        const connectorClass = document.getElementById('connector-class').value;
        const tasks = parseInt(document.getElementById('connector-tasks').value);
        const configText = document.getElementById('connector-config').value.trim();

        if (!name || !connectorClass || !configText) {
            Toast.error('필수 항목을 모두 입력해주세요.');
            return;
        }

        try {
            const config = JSON.parse(configText);
            
            const connectorConfig = {
                name,
                config: {
                    'connector.class': connectorClass,
                    'tasks.max': tasks.toString(),
                    ...config
                }
            };

            Loading.show();
            await api.createConnector(this.currentConnectId, connectorConfig);
            
            Toast.success('✅ 커넥터가 생성되었습니다.');
            document.getElementById('create-connector-modal').classList.remove('show');
            await this.loadConnectors();
            
        } catch (error) {
            console.error('커넥터 생성 실패:', error);
            if (error.message.includes('JSON')) {
                Toast.error('❌ JSON 형식이 올바르지 않습니다.');
            } else {
                Toast.error(`❌ 커넥터 생성 실패: ${error.message}`);
            }
        } finally {
            Loading.hide();
        }
    }

    /**
     * 상세 정보 보기
     */
    async viewDetails(connectorName) {
        try {
            Loading.show();
            const details = await api.getConnectorDetails(this.currentConnectId, connectorName);
            const status = await api.getConnectorStatus(this.currentConnectId, connectorName);
            
            document.getElementById('connector-detail-title').textContent = `커넥터: ${connectorName}`;
            document.getElementById('connector-detail-content').innerHTML = `
                <div class="detail-section">
                    <h4>기본 정보</h4>
                    <table class="info-table">
                        <tr>
                            <th>이름</th>
                            <td>${details.name}</td>
                        </tr>
                        <tr>
                            <th>클래스</th>
                            <td><code>${details.config['connector.class']}</code></td>
                        </tr>
                        <tr>
                            <th>태스크 수</th>
                            <td>${details.config['tasks.max']}</td>
                        </tr>
                        <tr>
                            <th>상태</th>
                            <td>${this.renderStatusBadge(status.connector.state)}</td>
                        </tr>
                    </table>
                </div>
                
                <div class="detail-section">
                    <h4>태스크 상태</h4>
                    ${status.tasks.map((task, idx) => `
                        <div class="task-status">
                            <span>Task ${idx}:</span>
                            ${this.renderStatusBadge(task.state)}
                            ${task.trace ? `<small class="text-danger">${task.trace}</small>` : ''}
                        </div>
                    `).join('')}
                </div>
                
                <div class="detail-section">
                    <h4>설정</h4>
                    <pre><code>${JSON.stringify(details.config, null, 2)}</code></pre>
                </div>
            `;
            
            document.getElementById('connector-detail-modal').classList.add('show');
        } catch (error) {
            console.error('상세 정보 로드 실패:', error);
            Toast.error('상세 정보를 불러올 수 없습니다.');
        } finally {
            Loading.hide();
        }
    }

    /**
     * 커넥터 일시정지
     */
    async pauseConnector(connectorName) {
        if (!confirm(`커넥터 "${connectorName}"를 일시정지하시겠습니까?`)) {
            return;
        }

        try {
            Loading.show();
            await api.pauseConnector(this.currentConnectId, connectorName);
            Toast.success(`✅ 커넥터가 일시정지되었습니다: ${connectorName}`);
            await this.loadConnectors();
        } catch (error) {
            console.error('커넥터 일시정지 실패:', error);
            Toast.error(`❌ 일시정지 실패: ${error.message}`);
        } finally {
            Loading.hide();
        }
    }

    /**
     * 커넥터 재개
     */
    async resumeConnector(connectorName) {
        try {
            Loading.show();
            await api.resumeConnector(this.currentConnectId, connectorName);
            Toast.success(`✅ 커넥터가 재개되었습니다: ${connectorName}`);
            await this.loadConnectors();
        } catch (error) {
            console.error('커넥터 재개 실패:', error);
            Toast.error(`❌ 재개 실패: ${error.message}`);
        } finally {
            Loading.hide();
        }
    }

    /**
     * 커넥터 재시작
     */
    async restartConnector(connectorName) {
        if (!confirm(`커넥터 "${connectorName}"를 재시작하시겠습니까?`)) {
            return;
        }

        try {
            Loading.show();
            await api.restartConnector(this.currentConnectId, connectorName);
            Toast.success(`✅ 커넥터가 재시작되었습니다: ${connectorName}`);
            await this.loadConnectors();
        } catch (error) {
            console.error('커넥터 재시작 실패:', error);
            Toast.error(`❌ 재시작 실패: ${error.message}`);
        } finally {
            Loading.hide();
        }
    }

    /**
     * 커넥터 삭제
     */
    async deleteConnector(connectorName) {
        if (!confirm(`커넥터 "${connectorName}"를 삭제하시겠습니까?\n\n이 작업은 되돌릴 수 없습니다.`)) {
            return;
        }

        try {
            Loading.show();
            await api.deleteConnector(this.currentConnectId, connectorName);
            Toast.success(`✅ 커넥터가 삭제되었습니다: ${connectorName}`);
            await this.loadConnectors();
        } catch (error) {
            console.error('커넥터 삭제 실패:', error);
            Toast.error(`❌ 삭제 실패: ${error.message}`);
        } finally {
            Loading.hide();
        }
    }
}

// 전역 인스턴스
const connectorManager = new ConnectorManager();

// 모달 닫기 함수
function closeModal(modalId) {
    document.getElementById(modalId)?.classList.remove('show');
}
