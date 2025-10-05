/**
 * WebSocket 클라이언트 - 실시간 데이터 업데이트
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
     * WebSocket 연결
     */
    connect() {
        try {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/ws`;
            
            this.ws = new WebSocket(wsUrl);
            
            this.ws.onopen = () => {
                console.log('WebSocket 연결됨');
                this.isConnected = true;
                this.reconnectAttempts = 0;
                this.emit('connected');
                
                // 연결 상태 UI 업데이트
                this.updateConnectionStatus(true);
            };

            this.ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.handleMessage(data);
                } catch (error) {
                    console.error('WebSocket 메시지 파싱 오류:', error);
                }
            };

            this.ws.onclose = (event) => {
                console.log('WebSocket 연결 종료:', event.code, event.reason);
                this.isConnected = false;
                this.updateConnectionStatus(false);
                
                // 자동 재연결 시도
                if (this.reconnectAttempts < this.maxReconnectAttempts) {
                    this.reconnectAttempts++;
                    console.log(`재연결 시도 ${this.reconnectAttempts}/${this.maxReconnectAttempts}`);
                    setTimeout(() => this.connect(), this.reconnectInterval);
                } else {
                    console.error('WebSocket 재연결 실패');
                    this.emit('reconnect_failed');
                }
            };

            this.ws.onerror = (error) => {
                console.error('WebSocket 오류:', error);
                this.emit('error', error);
            };

        } catch (error) {
            console.error('WebSocket 연결 실패:', error);
        }
    }

    /**
     * WebSocket 연결 종료
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
     * 메시지 전송
     */
    send(data) {
        if (this.isConnected && this.ws) {
            this.ws.send(JSON.stringify(data));
        } else {
            console.warn('WebSocket이 연결되지 않음');
        }
    }

    /**
     * 메시지 처리
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
                console.log('알 수 없는 메시지 타입:', type);
        }
    }

    /**
     * 이벤트 리스너 등록
     */
    on(event, callback) {
        if (!this.listeners.has(event)) {
            this.listeners.set(event, []);
        }
        this.listeners.get(event).push(callback);
    }

    /**
     * 이벤트 리스너 제거
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
     * 이벤트 발생
     */
    emit(event, data = null) {
        if (this.listeners.has(event)) {
            this.listeners.get(event).forEach(callback => {
                try {
                    callback(data);
                } catch (error) {
                    console.error(`이벤트 핸들러 오류 (${event}):`, error);
                }
            });
        }
    }

    /**
     * 연결 상태 UI 업데이트
     */
    updateConnectionStatus(connected) {
        const statusElement = document.getElementById('connection-status');
        if (statusElement) {
            statusElement.className = `connection-status ${connected ? 'connected' : 'disconnected'}`;
            statusElement.innerHTML = connected 
                ? '<i class="fas fa-wifi"></i> 연결됨'
                : '<i class="fas fa-wifi-slash"></i> 연결 끊김';
        }
    }

    /**
     * 특정 토픽 구독
     */
    subscribeTopic(topicName) {
        this.send({
            action: 'subscribe',
            resource: 'topic',
            name: topicName
        });
    }

    /**
     * 특정 스키마 구독
     */
    subscribeSchema(subject) {
        this.send({
            action: 'subscribe',
            resource: 'schema',
            subject: subject
        });
    }


    /**
     * 시스템 알림 구독
     */
    subscribeSystemAlerts() {
        this.send({
            action: 'subscribe',
            resource: 'system_alerts'
        });
    }
}

/**
 * 실시간 알림 관리자
 */
class RealtimeNotificationManager {
    constructor(wsClient) {
        this.wsClient = wsClient;
        this.setupEventListeners();
    }

    setupEventListeners() {
        // 토픽 이벤트
        this.wsClient.on('topic_created', (data) => {
            Toast.success(`토픽 '${data.name}'이 생성되었습니다.`);
            this.refreshTopicList();
        });

        this.wsClient.on('topic_updated', (data) => {
            Toast.info(`토픽 '${data.name}'이 업데이트되었습니다.`);
            this.refreshTopicList();
        });

        this.wsClient.on('topic_deleted', (data) => {
            Toast.warning(`토픽 '${data.name}'이 삭제되었습니다.`);
            this.refreshTopicList();
        });

        // 스키마 이벤트
        this.wsClient.on('schema_registered', (data) => {
            Toast.success(`스키마 '${data.subject}'가 등록되었습니다.`);
            this.refreshSchemaList();
        });

        this.wsClient.on('schema_updated', (data) => {
            Toast.info(`스키마 '${data.subject}'가 업데이트되었습니다.`);
            this.refreshSchemaList();
        });


        // 시스템 알림
        this.wsClient.on('system_alert', (data) => {
            const toastType = data.severity === 'error' ? 'error' : 
                             data.severity === 'warning' ? 'warning' : 'info';
            Toast[toastType](data.message);
        });

        // 연결 상태
        this.wsClient.on('connected', () => {
            Toast.success('실시간 연결이 설정되었습니다.');
        });

        this.wsClient.on('reconnect_failed', () => {
            Toast.error('실시간 연결에 실패했습니다. 페이지를 새로고침해주세요.');
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
 * WebSocket 초기화
 * 
 * 참고: 현재 백엔드에 WebSocket 엔드포인트가 구현되지 않았습니다.
 * WebSocket 기능이 필요한 경우 백엔드에 /ws 엔드포인트를 추가해야 합니다.
 */
function initializeWebSocket() {
    // WebSocket 기능 비활성화됨
    console.log('WebSocket 기능은 현재 비활성화되어 있습니다.');
    
    // 연결 상태를 disconnected로 표시
    const statusElement = document.getElementById('connection-status');
    if (statusElement) {
        statusElement.className = 'connection-status disconnected';
        statusElement.innerHTML = '<i class="fas fa-plug"></i> 연결 안 함';
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
