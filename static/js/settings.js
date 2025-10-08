/**
 * Settings Page - Cluster/Registry/Storage 관리
 */

class SettingsManager {
    constructor() {
        this.currentCluster = null;
        this.currentRegistry = null;
        this.currentStorage = null;
        this.currentConnect = null;
    }

    async init() {
        await this.loadClusters();
        await this.loadRegistries();
        await this.loadStorages();
        await this.loadConnects();  // Kafka Connect 목록 로드 추가
        this.setupEventListeners();
        this.loadCurrentSettings();
    }

    /**
     * 클러스터 목록 로드
     */
    async loadClusters() {
        try {
            const clusters = await api.getKafkaClusters();
            const container = document.getElementById('kafka-clusters-list');

            if (!clusters || clusters.length === 0) {
                container.innerHTML = '<p class="empty-message">등록된 클러스터가 없습니다.</p>';
                return;
            }

            // 선택된 클러스터가 없으면 첫 번째 클러스터 자동 선택
            const currentSettings = api.getCurrentSettings();
            if (!currentSettings.clusterId || currentSettings.clusterId === 'default') {
                if (clusters.length > 0) {
                    api.setClusterId(clusters[0].cluster_id);
                    this.currentCluster = clusters[0].cluster_id;
                    console.log('첫 번째 클러스터 자동 선택:', clusters[0].cluster_id);
                }
            }

            container.innerHTML = clusters.map(cluster => `
                <div class="cluster-item" data-id="${cluster.cluster_id}">
                    <div class="cluster-info">
                        <h4>${cluster.name}</h4>
                        <p>${cluster.bootstrap_servers}</p>
                        <span class="badge ${cluster.is_active ? 'badge-success' : 'badge-danger'}">
                            ${cluster.is_active ? 'Active' : 'Inactive'}
                        </span>
                    </div>
                    <div class="cluster-actions">
                        <button class="btn btn-sm btn-primary" onclick="settingsManager.selectCluster('${cluster.cluster_id}')">
                            <i class="fas fa-check"></i> 선택
                        </button>
                        <button class="btn btn-sm btn-secondary" onclick="settingsManager.testCluster('${cluster.cluster_id}')">
                            <i class="fas fa-plug"></i> 연결 테스트
                        </button>
                        <button class="btn btn-sm btn-danger" onclick="settingsManager.deleteCluster('${cluster.cluster_id}')">
                            <i class="fas fa-trash"></i> 삭제
                        </button>
                    </div>
                </div>
            `).join('');

        } catch (error) {
            console.error('클러스터 로드 실패:', error);
            showToast('클러스터 목록을 불러오지 못했습니다.', 'error');
        }
    }

    /**
     * Schema Registry 목록 로드
     */
    async loadRegistries() {
        try {
            const registries = await api.getSchemaRegistries(true);
            const container = document.getElementById('registries-list');
            
            if (!registries || registries.length === 0) {
                container.innerHTML = '<p class="empty-message">등록된 레지스트리가 없습니다.</p>';
                return;
            }

            // 선택된 레지스트리가 없으면 첫 번째 자동 선택
            const currentSettings = api.getCurrentSettings();
            if (!currentSettings.registryId || currentSettings.registryId === 'default') {
                if (registries.length > 0) {
                    api.setRegistryId(registries[0].registry_id);
                    this.currentRegistry = registries[0].registry_id;
                    console.log('첫 번째 레지스트리 자동 선택:', registries[0].registry_id);
                }
            }

            container.innerHTML = registries.map(registry => `
                <div class="cluster-item" data-id="${registry.registry_id}">
                    <div class="cluster-info">
                        <h4>${registry.name}</h4>
                        <p>${registry.url}</p>
                        <span class="badge ${registry.is_active ? 'badge-success' : 'badge-danger'}">
                            ${registry.is_active ? 'Active' : 'Inactive'}
                        </span>
                    </div>
                    <div class="cluster-actions">
                        <button class="btn btn-sm btn-primary" onclick="settingsManager.selectRegistry('${registry.registry_id}')">
                            <i class="fas fa-check"></i> 선택
                        </button>
                        <button class="btn btn-sm btn-secondary" onclick="settingsManager.testRegistry('${registry.registry_id}')">
                            <i class="fas fa-plug"></i> 연결 테스트
                        </button>
                        <button class="btn btn-sm btn-danger" onclick="settingsManager.deleteRegistry('${registry.registry_id}')">
                            <i class="fas fa-trash"></i> 삭제
                        </button>
                    </div>
                </div>
            `).join('');

        } catch (error) {
            console.error('레지스트리 로드 실패:', error);
            showToast('레지스트리 목록을 불러오지 못했습니다.', 'error');
        }
    }

    /**
     * Object Storage 목록 로드
     */
    async loadStorages() {
        try {
            const storages = await api.getObjectStorages(true);
            const container = document.getElementById('storages-list');
            
            if (!storages || storages.length === 0) {
                container.innerHTML = '<p class="empty-message">등록된 스토리지가 없습니다.</p>';
                return;
            }

            container.innerHTML = storages.map(storage => `
                <div class="cluster-item" data-id="${storage.storage_id}">
                    <div class="cluster-info">
                        <h4>${storage.name}</h4>
                        <p>${storage.endpoint_url} / ${storage.bucket_name}</p>
                        <span class="badge ${storage.is_active ? 'badge-success' : 'badge-danger'}">
                            ${storage.is_active ? 'Active' : 'Inactive'}
                        </span>
                    </div>
                    <div class="cluster-actions">
                        <button class="btn btn-sm btn-primary" onclick="settingsManager.selectStorage('${storage.storage_id}')">
                            <i class="fas fa-check"></i> 선택
                        </button>
                        <button class="btn btn-sm btn-secondary" onclick="settingsManager.testStorage('${storage.storage_id}')">
                            <i class="fas fa-plug"></i> 연결 테스트
                        </button>
                        <button class="btn btn-sm btn-danger" onclick="settingsManager.deleteStorage('${storage.storage_id}')">
                            <i class="fas fa-trash"></i> 삭제
                        </button>
                    </div>
                </div>
            `).join('');

        } catch (error) {
            console.error('스토리지 로드 실패:', error);
            showToast('스토리지 목록을 불러오지 못했습니다.', 'error');
        }
    }

    /**
     * Kafka Connect 목록 로드
     */
    async loadConnects() {
        try {
            const connects = await api.getKafkaConnects();
            const container = document.getElementById('connects-list');
            
            if (!connects || connects.length === 0) {
                container.innerHTML = '<p class="empty-message">등록된 Kafka Connect가 없습니다.</p>';
                return;
            }

            container.innerHTML = connects.map(connect => `
                <div class="cluster-item" data-id="${connect.connect_id}">
                    <div class="cluster-info">
                        <h4>${connect.name}</h4>
                        <p>${connect.url}</p>
                        <small>Cluster: ${connect.cluster_id}</small>
                        <span class="badge ${connect.is_active ? 'badge-success' : 'badge-danger'}">
                            ${connect.is_active ? 'Active' : 'Inactive'}
                        </span>
                    </div>
                    <div class="cluster-actions">
                        <button class="btn btn-sm btn-primary" onclick="settingsManager.selectConnect('${connect.connect_id}')">
                            <i class="fas fa-check"></i> 선택
                        </button>
                        <button class="btn btn-sm btn-secondary" onclick="settingsManager.testConnect('${connect.connect_id}')">
                            <i class="fas fa-plug"></i> 연결 테스트
                        </button>
                        <button class="btn btn-sm btn-danger" onclick="settingsManager.deleteConnect('${connect.connect_id}')">
                            <i class="fas fa-trash"></i> 삭제
                        </button>
                    </div>
                </div>
            `).join('');

        } catch (error) {
            console.error('Kafka Connect 로드 실패:', error);
            showToast('Kafka Connect 목록을 불러오지 못했습니다.', 'error');
        }
    }

    /**
     * 클러스터 선택
     */
    selectCluster(clusterId) {
        api.setClusterId(clusterId);
        this.currentCluster = clusterId;
        showToast(`클러스터가 선택되었습니다: ${clusterId}`, 'success');
        this.highlightSelected('kafka-clusters-list', clusterId);
        this.updateCurrentSettings();
    }

    /**
     * 레지스트리 선택
     */
    selectRegistry(registryId) {
        api.setRegistryId(registryId);
        this.currentRegistry = registryId;
        showToast(`레지스트리가 선택되었습니다: ${registryId}`, 'success');
        this.highlightSelected('registries-list', registryId);
        this.updateCurrentSettings();
    }

    /**
     * 스토리지 선택
     */
    selectStorage(storageId) {
        api.setStorageId(storageId);
        this.currentStorage = storageId;
        showToast(`스토리지가 선택되었습니다: ${storageId}`, 'success');
        this.highlightSelected('storages-list', storageId);
        this.updateCurrentSettings();
    }
    
    /**
     * Kafka Connect 선택
     */
    selectConnect(connectId) {
        api.setConnectId(connectId);
        this.currentConnect = connectId;
        showToast(`Kafka Connect가 선택되었습니다: ${connectId}`, 'success');
        this.updateCurrentSettings();
    }

    /**
     * 선택 항목 하이라이트
     */
    highlightSelected(containerId, selectedId) {
        const container = document.getElementById(containerId);
        container.querySelectorAll('.cluster-item').forEach(item => {
            item.classList.remove('selected');
            if (item.dataset.id === selectedId) {
                item.classList.add('selected');
            }
        });
    }

    /**
     * 클러스터 연결 테스트
     */
    async testCluster(clusterId) {
        try {
            showToast('연결 테스트 중...', 'info');
            const result = await api.testKafkaConnection(clusterId);
            
            if (result.success) {
                showToast(`✅ 연결 성공! (${result.latency_ms?.toFixed(0)}ms) - ${result.message}`, 'success');
            } else {
                showToast(`❌ 연결 실패: ${result.message}`, 'error');
            }
        } catch (error) {
            console.error('연결 테스트 실패:', error);
            showToast(`연결 테스트 실패: ${error.message}`, 'error');
        }
    }

    /**
     * 레지스트리 연결 테스트
     */
    async testRegistry(registryId) {
        try {
            showToast('연결 테스트 중...', 'info');
            const result = await api.testSchemaRegistryConnection(registryId);
            
            if (result.success) {
                showToast(`✅ 연결 성공! (${result.latency_ms?.toFixed(0)}ms) - ${result.message}`, 'success');
            } else {
                showToast(`❌ 연결 실패: ${result.message}`, 'error');
            }
        } catch (error) {
            console.error('연결 테스트 실패:', error);
            showToast(`연결 테스트 실패: ${error.message}`, 'error');
        }
    }

    /**
     * 스토리지 연결 테스트
     */
    async testStorage(storageId) {
        try {
            showToast('연결 테스트 중...', 'info');
            const result = await api.testObjectStorageConnection(storageId);
            
            if (result.success) {
                showToast(`✅ 연결 성공! (${result.latency_ms?.toFixed(0)}ms) - ${result.message}`, 'success');
            } else {
                showToast(`❌ 연결 실패: ${result.message}`, 'error');
            }
        } catch (error) {
            console.error('연결 테스트 실패:', error);
            showToast(`연결 테스트 실패: ${error.message}`, 'error');
        }
    }

    /**
     * Kafka Connect 연결 테스트
     */
    async testConnect(connectId) {
        try {
            showToast('연결 테스트 중...', 'info');
            const result = await api.testKafkaConnectConnection(connectId);
            
            if (result.success) {
                const connectorCount = result.metadata?.connector_count || 0;
                showToast(`✅ 연결 성공! (${result.latency_ms?.toFixed(0)}ms) - Connectors: ${connectorCount}개`, 'success');
            } else {
                showToast(`❌ 연결 실패: ${result.message}`, 'error');
            }
        } catch (error) {
            console.error('연결 테스트 실패:', error);
            showToast(`연결 테스트 실패: ${error.message}`, 'error');
        }
    }

    /**
     * 클러스터 삭제
     */
    async deleteCluster(clusterId) {
        if (!confirm('정말로 이 Kafka 클러스터를 삭제하시겠습니까?')) {
            return;
        }

        try {
            showToast('삭제 중...', 'info');
            await api.deleteKafkaCluster(clusterId);
            showToast('✅ 클러스터가 삭제되었습니다.', 'success');
            await this.loadClusters();
        } catch (error) {
            console.error('삭제 실패:', error);
            showToast(`❌ 삭제 실패: ${error.message}`, 'error');
        }
    }

    /**
     * 레지스트리 삭제
     */
    async deleteRegistry(registryId) {
        if (!confirm('정말로 이 Schema Registry를 삭제하시겠습니까?')) {
            return;
        }

        try {
            showToast('삭제 중...', 'info');
            await api.deleteSchemaRegistry(registryId);
            showToast('✅ 레지스트리가 삭제되었습니다.', 'success');
            await this.loadRegistries();
        } catch (error) {
            console.error('삭제 실패:', error);
            showToast(`❌ 삭제 실패: ${error.message}`, 'error');
        }
    }

    /**
     * 스토리지 삭제
     */
    async deleteStorage(storageId) {
        if (!confirm('정말로 이 Object Storage를 삭제하시겠습니까?')) {
            return;
        }

        try {
            showToast('삭제 중...', 'info');
            await api.deleteObjectStorage(storageId);
            showToast('✅ 스토리지가 삭제되었습니다.', 'success');
            await this.loadStorages();
        } catch (error) {
            console.error('삭제 실패:', error);
            showToast(`❌ 삭제 실패: ${error.message}`, 'error');
        }
    }

    /**
     * Kafka Connect 삭제
     */
    async deleteConnect(connectId) {
        if (!confirm('정말로 이 Kafka Connect를 삭제하시겠습니까?')) {
            return;
        }

        try {
            showToast('삭제 중...', 'info');
            await api.deleteKafkaConnect(connectId);
            showToast('✅ Kafka Connect가 삭제되었습니다.', 'success');
            await this.loadConnects();
        } catch (error) {
            console.error('삭제 실패:', error);
            showToast(`❌ 삭제 실패: ${error.message}`, 'error');
        }
    }

    /**
     * 현재 설정 로드
     */
    loadCurrentSettings() {
        const settings = api.getCurrentSettings();
        this.currentCluster = settings.clusterId;
        this.currentRegistry = settings.registryId;
        this.currentStorage = settings.storageId;
        this.currentConnect = settings.connectId;
        this.updateCurrentSettings();
    }

    /**
     * 현재 설정 표시 업데이트
     */
    updateCurrentSettings() {
        const settingsDisplay = document.getElementById('current-settings');
        if (settingsDisplay) {
            settingsDisplay.innerHTML = `
                <div class="current-setting">
                    <span class="label">Kafka Cluster:</span>
                    <span class="value">${this.currentCluster || 'default'}</span>
                </div>
                <div class="current-setting">
                    <span class="label">Schema Registry:</span>
                    <span class="value">${this.currentRegistry || 'default'}</span>
                </div>
                <div class="current-setting">
                    <span class="label">Minio/S3:</span>
                    <span class="value">${this.currentStorage || 'none'}</span>
                </div>
                <div class="current-setting">
                    <span class="label">Kafka Connect:</span>
                    <span class="value">${this.currentConnect || 'none'}</span>
                </div>
            `;
        }
    }

    /**
     * 이벤트 리스너 설정
     */
    setupEventListeners() {
        // 새로고침 버튼
        const refreshBtn = document.getElementById('refresh-all');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', async () => {
                await this.init();
                showToast('설정을 새로고침했습니다.', 'success');
            });
        }
    }

    /**
     * 모달 열기
     */
    openModal(content) {
        const overlay = document.getElementById('modal-overlay');
        const container = document.getElementById('modal-container');
        
        container.innerHTML = content;
        overlay.classList.add('show');
        container.classList.add('show');
    }

    /**
     * 모달 닫기
     */
    closeModal() {
        const overlay = document.getElementById('modal-overlay');
        const container = document.getElementById('modal-container');
        
        overlay.classList.remove('show');
        container.classList.remove('show');
    }

    /**
     * Kafka Cluster 생성 모달
     */
    showCreateClusterModal() {
        const content = `
            <div class="modal-header">
                <h2><i class="fas fa-server"></i> Kafka 클러스터 추가</h2>
            </div>
            <div class="modal-body">
                <form id="create-cluster-form">
                    <div class="form-group">
                        <label for="cluster_id">클러스터 ID *</label>
                        <input type="text" id="cluster_id" name="cluster_id" required placeholder="prod-cluster">
                        <small>고유한 클러스터 식별자</small>
                    </div>
                    <div class="form-group">
                        <label for="name">이름 *</label>
                        <input type="text" id="name" name="name" required placeholder="Production Cluster">
                    </div>
                    <div class="form-group">
                        <label for="bootstrap_servers">Bootstrap Servers *</label>
                        <input type="text" id="bootstrap_servers" name="bootstrap_servers" required 
                               placeholder="broker1:9092,broker2:9092">
                        <small>쉼표로 구분된 브로커 주소</small>
                    </div>
                    <div class="form-group">
                        <label for="description">설명</label>
                        <textarea id="description" name="description" rows="2" 
                                  placeholder="프로덕션 환경 Kafka 클러스터"></textarea>
                    </div>
                </form>
            </div>
            <div class="modal-footer">
                <button class="btn btn-secondary" onclick="settingsManager.closeModal()">
                    취소
                </button>
                <button class="btn btn-primary" onclick="settingsManager.createCluster()">
                    <i class="fas fa-save"></i> 생성
                </button>
            </div>
        `;
        this.openModal(content);
    }

    /**
     * Kafka Cluster 생성
     */
    async createCluster() {
        const form = document.getElementById('create-cluster-form');
        const formData = new FormData(form);
        const data = Object.fromEntries(formData);

        try {
            showToast('클러스터 생성 중...', 'info');
            await api.createKafkaCluster(data);
            showToast('✅ 클러스터가 생성되었습니다.', 'success');
            this.closeModal();
            await this.loadClusters();
        } catch (error) {
            console.error('클러스터 생성 실패:', error);
            showToast(`❌ 생성 실패: ${error.message}`, 'error');
        }
    }

    /**
     * Schema Registry 생성 모달
     */
    showCreateRegistryModal() {
        const content = `
            <div class="modal-header">
                <h2><i class="fas fa-database"></i> Schema Registry 추가</h2>
            </div>
            <div class="modal-body">
                <form id="create-registry-form">
                    <div class="form-group">
                        <label for="registry_id">레지스트리 ID *</label>
                        <input type="text" id="registry_id" name="registry_id" required placeholder="prod-registry">
                    </div>
                    <div class="form-group">
                        <label for="name">이름 *</label>
                        <input type="text" id="name" name="name" required placeholder="Production Registry">
                    </div>
                    <div class="form-group">
                        <label for="url">URL *</label>
                        <input type="text" id="url" name="url" required placeholder="http://localhost:8081">
                    </div>
                    <div class="form-group">
                        <label for="description">설명</label>
                        <textarea id="description" name="description" rows="2"></textarea>
                    </div>
                </form>
            </div>
            <div class="modal-footer">
                <button class="btn btn-secondary" onclick="settingsManager.closeModal()">취소</button>
                <button class="btn btn-primary" onclick="settingsManager.createRegistry()">
                    <i class="fas fa-save"></i> 생성
                </button>
            </div>
        `;
        this.openModal(content);
    }

    /**
     * Schema Registry 생성
     */
    async createRegistry() {
        const form = document.getElementById('create-registry-form');
        const formData = new FormData(form);
        const data = Object.fromEntries(formData);

        try {
            showToast('레지스트리 생성 중...', 'info');
            await api.createSchemaRegistry(data);
            showToast('✅ 레지스트리가 생성되었습니다.', 'success');
            this.closeModal();
            await this.loadRegistries();
        } catch (error) {
            console.error('레지스트리 생성 실패:', error);
            showToast(`❌ 생성 실패: ${error.message}`, 'error');
        }
    }

    /**
     * Object Storage 생성 모달
     */
    showCreateStorageModal() {
        const content = `
            <div class="modal-header">
                <h2><i class="fas fa-hdd"></i> Object Storage 추가</h2>
            </div>
            <div class="modal-body">
                <form id="create-storage-form">
                    <div class="form-group">
                        <label for="storage_id">스토리지 ID *</label>
                        <input type="text" id="storage_id" name="storage_id" required placeholder="minio-prod">
                    </div>
                    <div class="form-group">
                        <label for="name">이름 *</label>
                        <input type="text" id="name" name="name" required placeholder="MinIO Production">
                    </div>
                    <div class="form-group">
                        <label for="endpoint_url">Endpoint URL *</label>
                        <input type="text" id="endpoint_url" name="endpoint_url" required placeholder="localhost:9000">
                    </div>
                    <div class="form-group">
                        <label for="access_key">Access Key *</label>
                        <input type="text" id="access_key" name="access_key" required>
                    </div>
                    <div class="form-group">
                        <label for="secret_key">Secret Key *</label>
                        <input type="password" id="secret_key" name="secret_key" required>
                    </div>
                    <div class="form-group">
                        <label for="bucket_name">Bucket Name *</label>
                        <input type="text" id="bucket_name" name="bucket_name" required placeholder="schemas">
                    </div>
                </form>
            </div>
            <div class="modal-footer">
                <button class="btn btn-secondary" onclick="settingsManager.closeModal()">취소</button>
                <button class="btn btn-primary" onclick="settingsManager.createStorage()">
                    <i class="fas fa-save"></i> 생성
                </button>
            </div>
        `;
        this.openModal(content);
    }

    /**
     * Object Storage 생성
     */
    async createStorage() {
        const form = document.getElementById('create-storage-form');
        const formData = new FormData(form);
        const data = Object.fromEntries(formData);

        try {
            showToast('스토리지 생성 중...', 'info');
            await api.createObjectStorage(data);
            showToast('✅ 스토리지가 생성되었습니다.', 'success');
            this.closeModal();
            await this.loadStorages();
        } catch (error) {
            console.error('스토리지 생성 실패:', error);
            showToast(`❌ 생성 실패: ${error.message}`, 'error');
        }
    }

    /**
     * Kafka Connect 생성 모달
     */
    showCreateConnectModal() {
        const content = `
            <div class="modal-header">
                <h2><i class="fas fa-plug"></i> Kafka Connect 추가</h2>
            </div>
            <div class="modal-body">
                <form id="create-connect-form">
                    <div class="form-group">
                        <label for="connect_id">Connect ID *</label>
                        <input type="text" id="connect_id" name="connect_id" required placeholder="connect-prod-01">
                    </div>
                    <div class="form-group">
                        <label for="cluster_id">Kafka Cluster ID *</label>
                        <input type="text" id="cluster_id" name="cluster_id" required placeholder="prod-cluster">
                        <small>연관된 Kafka 클러스터 ID</small>
                    </div>
                    <div class="form-group">
                        <label for="name">이름 *</label>
                        <input type="text" id="name" name="name" required placeholder="Production Kafka Connect">
                    </div>
                    <div class="form-group">
                        <label for="url">URL *</label>
                        <input type="text" id="url" name="url" required placeholder="http://localhost:8083">
                    </div>
                    <div class="form-group">
                        <label for="description">설명</label>
                        <textarea id="description" name="description" rows="2"></textarea>
                    </div>
                </form>
            </div>
            <div class="modal-footer">
                <button class="btn btn-secondary" onclick="settingsManager.closeModal()">취소</button>
                <button class="btn btn-primary" onclick="settingsManager.createConnect()">
                    <i class="fas fa-save"></i> 생성
                </button>
            </div>
        `;
        this.openModal(content);
    }

    /**
     * Kafka Connect 생성
     */
    async createConnect() {
        const form = document.getElementById('create-connect-form');
        const formData = new FormData(form);
        const data = Object.fromEntries(formData);

        try {
            showToast('Kafka Connect 생성 중...', 'info');
            await api.createKafkaConnect(data);
            showToast('✅ Kafka Connect가 생성되었습니다.', 'success');
            this.closeModal();
            await this.loadConnects();
        } catch (error) {
            console.error('Kafka Connect 생성 실패:', error);
            showToast(`❌ 생성 실패: ${error.message}`, 'error');
        }
    }
}

/**
 * Toast 메시지 표시
 */
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.classList.add('show');
    }, 10);
    
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// 전역 인스턴스
const settingsManager = new SettingsManager();

// 페이지 로드 시 초기화
document.addEventListener('DOMContentLoaded', () => {
    settingsManager.init();
});
