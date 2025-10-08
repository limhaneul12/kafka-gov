/**
 * WebSocket Client - Realtime data updates
 */

class WebSocketClient {
    constructor() {
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectInterval = 5000; // 5초
        this.listeners = new Map();
        this.isConnected = false;
    }

    /**
     * WebSocket connect
     */
    connect() {
        try {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/ws`;
            
            this.ws = new WebSocket(wsUrl);
            
            this.ws.onopen = () => {
                console.log('WebSocket connected');
                this.isConnected = true;
                this.reconnectAttempts = 0;
                this.emit('connected');
                
                // Update connection status UI
                this.updateConnectionStatus(true);
            };

            this.ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.handleMessage(data);
                } catch (error) {
                    console.error('WebSocket message parse error:', error);
                }
            };

            this.ws.onclose = (event) => {
                console.log('WebSocket closed:', event.code, event.reason);
                this.isConnected = false;
                this.updateConnectionStatus(false);
                
                // Auto-reconnect
                if (this.reconnectAttempts < this.maxReconnectAttempts) {
                    this.reconnectAttempts++;
                    console.log(`Reconnect attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts}`);
                    setTimeout(() => this.connect(), this.reconnectInterval);
                } else {
                    console.error('WebSocket reconnect failed');
                    this.emit('reconnect_failed');
                }
            };

            this.ws.onerror = (error) => {
                console.error('WebSocket error:', error);
                this.emit('error', error);
            };

        } catch (error) {
            console.error('WebSocket connection failed:', error);
        }
    }

    /**
     * WebSocket disconnect
     */
    disconnect() {
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
        this.isConnected = false;
        this.updateConnectionStatus(false);
    }

    /**
     * Send message
     */
    send(data) {
        if (this.isConnected && this.ws) {
            this.ws.send(JSON.stringify(data));
        } else {
            console.warn('WebSocket is not connected');
        }
    }

    /**
     * Handle message
     */
    handleMessage(data) {
        const { type, payload } = data;
        
        switch (type) {
            case 'topic_created':
                this.emit('topic_created', payload);
                break;
            case 'topic_updated':
                this.emit('topic_updated', payload);
                break;
            case 'topic_deleted':
                this.emit('topic_deleted', payload);
                break;
            case 'schema_registered':
                this.emit('schema_registered', payload);
                break;
            case 'schema_updated':
                this.emit('schema_updated', payload);
                break;
            case 'system_alert':
                this.emit('system_alert', payload);
                break;
            default:
                console.log('Unknown message type:', type);
        }
    }

    /**
     * Add event listener
     */
    on(event, callback) {
        if (!this.listeners.has(event)) {
            this.listeners.set(event, []);
        }
        this.listeners.get(event).push(callback);
    }

    /**
     * Remove event listener
     */
    off(event, callback) {
        if (this.listeners.has(event)) {
            const callbacks = this.listeners.get(event);
            const index = callbacks.indexOf(callback);
            if (index > -1) {
                callbacks.splice(index, 1);
            }
        }
    }

    /**
     * Emit event
     */
    emit(event, data = null) {
        if (this.listeners.has(event)) {
            this.listeners.get(event).forEach(callback => {
                try {
                    callback(data);
                } catch (error) {
                    console.error(`Event handler error (${event}):`, error);
                }
            });
        }
    }

    /**
     * Update connection status UI
     */
    updateConnectionStatus(connected) {
        const statusElement = document.getElementById('connection-status');
        if (statusElement) {
            statusElement.className = `connection-status ${connected ? 'connected' : 'disconnected'}`;
            statusElement.innerHTML = connected 
                ? '<i class="fas fa-wifi"></i> Connected'
                : '<i class="fas fa-wifi-slash"></i> Disconnected';
        }
    }

    /**
     * Subscribe topic
     */
    subscribeTopic(topicName) {
        this.send({
            action: 'subscribe',
            resource: 'topic',
            name: topicName
        });
    }

    /**
     * Subscribe schema
     */
    subscribeSchema(subject) {
        this.send({
            action: 'subscribe',
            resource: 'schema',
            subject: subject
        });
    }


    /**
     * Subscribe system alerts
     */
    subscribeSystemAlerts() {
        this.send({
            action: 'subscribe',
            resource: 'system_alerts'
        });
    }
}

/**
 * Realtime notification manager
 */
class RealtimeNotificationManager {
    constructor(wsClient) {
        this.wsClient = wsClient;
        this.setupEventListeners();
    }

    setupEventListeners() {
        // Topic events
        this.wsClient.on('topic_created', (data) => {
            Toast.success(`Topic '${data.name}' has been created.`);
            this.refreshTopicList();
        });

        this.wsClient.on('topic_updated', (data) => {
            Toast.info(`Topic '${data.name}' has been updated.`);
            this.refreshTopicList();
        });

        this.wsClient.on('topic_deleted', (data) => {
            Toast.warning(`Topic '${data.name}' has been deleted.`);
            this.refreshTopicList();
        });

        // Schema events
        this.wsClient.on('schema_registered', (data) => {
            Toast.success(`Schema '${data.subject}' has been registered.`);
            this.refreshSchemaList();
        });

        this.wsClient.on('schema_updated', (data) => {
            Toast.info(`Schema '${data.subject}' has been updated.`);
            this.refreshSchemaList();
        });


        // System alerts
        this.wsClient.on('system_alert', (data) => {
            const toastType = data.severity === 'error' ? 'error' : 
                             data.severity === 'warning' ? 'warning' : 'info';
            Toast[toastType](data.message);
        });

        // Connection state
        this.wsClient.on('connected', () => {
            Toast.success('Realtime connection established.');
        });

        this.wsClient.on('reconnect_failed', () => {
            Toast.error('Failed to establish realtime connection. Please refresh the page.');
        });
    }

    refreshTopicList() {
        if (window.kafkaGovApp && window.kafkaGovApp.currentTab === 'topics') {
            window.kafkaGovApp.loadTopics();
        }
    }

    refreshSchemaList() {
        if (window.kafkaGovApp && window.kafkaGovApp.currentTab === 'schemas') {
            window.kafkaGovApp.loadSchemas();
        }
    }

    refreshViolationsList() {
        if (window.kafkaGovApp && window.kafkaGovApp.currentTab === 'policies') {
            window.kafkaGovApp.loadPolicies();
        }
    }
}

// 전역 WebSocket 클라이언트
let wsClient = null;
let notificationManager = null;

/**
 * WebSocket initialization
 * Note: Backend WebSocket endpoint is not implemented yet.
 * If WebSocket is required, implement /ws endpoint in backend.
 */
function initializeWebSocket() {
    // WebSocket 기능 비활성화됨
    console.log('WebSocket is currently disabled.');
    
    // 연결 상태를 disconnected로 표시
    const statusElement = document.getElementById('connection-status');
    if (statusElement) {
        statusElement.className = 'connection-status disconnected';
        statusElement.innerHTML = '<i class="fas fa-plug"></i> Not connected';
    }
    
    // 실제 구현 시 아래 코드 활성화
    /*
    wsClient = new WebSocketClient();
    notificationManager = new RealtimeNotificationManager(wsClient);
    
    // 연결 시작
    wsClient.connect();
    
    // 기본 구독 설정
    wsClient.on('connected', () => {
        wsClient.subscribeSystemAlerts();
    });
    */
}

/**
 * WebSocket 정리
 */
function cleanupWebSocket() {
    if (wsClient) {
        wsClient.disconnect();
        wsClient = null;
        notificationManager = null;
    }
}

// 전역으로 노출
window.wsClient = wsClient;
window.initializeWebSocket = initializeWebSocket;
window.cleanupWebSocket = cleanupWebSocket;
