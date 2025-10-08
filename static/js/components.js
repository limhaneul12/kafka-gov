/**
 * UI 컴포넌트 - 재사용 가능한 UI 요소들
 */

// =================
// 토스트 알림
// =================
class Toast {
    static show(message, type = 'info', duration = 5000) {
        const container = document.getElementById('toast-container');
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.innerHTML = `
            <div style="display: flex; align-items: center; gap: 0.5rem;">
                <i class="fas ${this.getIcon(type)}"></i>
                <span>${message}</span>
                <button onclick="this.parentElement.parentElement.remove()" style="margin-left: auto; background: none; border: none; color: inherit; cursor: pointer;">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `;

        container.appendChild(toast);

        // 자동 제거
        setTimeout(() => {
            if (toast.parentElement) {
                toast.remove();
            }
        }, duration);
    }

    static getIcon(type) {
        const icons = {
            success: 'fa-check-circle',
            error: 'fa-exclamation-circle',
            warning: 'fa-exclamation-triangle',
            info: 'fa-info-circle'
        };
        return icons[type] || icons.info;
    }

    static success(message) {
        this.show(message, 'success');
    }

    static error(message) {
        this.show(message, 'error');
    }

    static warning(message) {
        this.show(message, 'warning');
    }

    static info(message) {
        this.show(message, 'info');
    }
}

// =================
// 로딩 스피너
// =================
class Loading {
    static show() {
        document.getElementById('loading').classList.add('active');
    }

    static hide() {
        document.getElementById('loading').classList.remove('active');
    }
}

// =================
// 모달 관리
// =================
class Modal {
    static show(modalId) {
        document.getElementById(modalId).classList.add('active');
    }

    static hide(modalId) {
        document.getElementById(modalId).classList.remove('active');
    }

    static hideAll() {
        document.querySelectorAll('.modal').forEach(modal => {
            modal.classList.remove('active');
        });
    }
}

// =================
// 테이블 렌더러
// =================
class TableRenderer {
    static escapeHtml(value) {
        if (value === undefined || value === null) {
            return '';
        }
        return String(value)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    static formatConfidence(score) {
        if (Number.isFinite(score)) {
            return `${(score * 100).toFixed(1)}%`;
        }
        return '-';
    }

    /**
     * 토픽 테이블 렌더링
     */
    static renderTopicsTable(topics) {
        const tbody = document.getElementById('topics-table-body');
        tbody.innerHTML = '';

        if (!topics || topics.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="9" style="text-align: center; padding: 2rem; color: var(--text-muted);">
                        No topics.
                    </td>
                </tr>
            `;
            return;
        }

        topics.forEach(topic => {
            const rawName = topic.topic_name ?? '';
            const name = this.escapeHtml(rawName);
            const owner = this.escapeHtml(topic.owner || '-');
            const doc = topic.doc;
            const docHtml = doc 
                ? `<a href="${this.escapeHtml(doc)}" target="_blank" rel="noopener noreferrer" title="문서 보기" style="color: var(--primary);">
                    <i class="fas fa-external-link-alt"></i>
                   </a>`
                : '<span style="color: var(--text-muted);">-</span>';
            const tags = topic.tags && topic.tags.length > 0 
                ? topic.tags.map(tag => {
                    const colorClass = TableRenderer.getTagColorClass(tag);
                    return `<span class="tag-badge ${colorClass}">${TableRenderer.escapeHtml(tag)}</span>`;
                  }).join(' ')
                : '<span style="color: var(--text-muted);">-</span>';
            const partitions = topic.partition_count ?? '-';
            const replicas = topic.replication_factor ?? '-';
            const rawEnv = topic.environment ?? '-';
            const environment = this.escapeHtml(rawEnv);
            const row = document.createElement('tr');
            row.innerHTML = `
                <td style="width: 40px;">
                    <input type="checkbox" class="topic-checkbox" value="${this.escapeHtml(rawName)}" onchange="window.kafkaGovApp.handleTopicCheckboxChange()">
                </td>
                <td>
                    <div style="font-weight: 500;">${name}</div>
                </td>
                <td>${owner}</td>
                <td style="text-align: center;">${docHtml}</td>
                <td><span style="font-size: 0.875rem;">${tags}</span></td>
                <td style="text-align: center;">${partitions}</td>
                <td style="text-align: center;">${replicas}</td>
                <td>
                    <span class="status-badge ${TableRenderer.getEnvClass(environment)}">${environment.toUpperCase()}</span>
                </td>
                <td>
                    <button class="btn-icon" onclick="deleteTopic(decodeURIComponent('${encodeURIComponent(rawName)}'))" title="삭제" style="color: var(--danger);">
                        <i class="fas fa-trash"></i>
                    </button>
                </td>
            `;
            tbody.appendChild(row);
        });
    }

    /**
     * 스키마 테이블 렌더링
     */
    static renderSchemasTable(schemas, appInstance) {
        const tbody = document.getElementById('schemas-table-body');
        tbody.innerHTML = '';

        if (!schemas || schemas.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="6" style="text-align: center; padding: 2rem; color: var(--text-muted);">
                        No schemas.
                    </td>
                </tr>
            `;
            return;
        }

        schemas.forEach(schema => {
            const rawSubject = schema.subject ?? '';
            const subject = this.escapeHtml(rawSubject);
            const environments = schema.environments.length > 0 ? schema.environments.map(env => this.escapeHtml(env)).join(', ') : '-';
            const owner = this.escapeHtml(schema.owner || '-');
            const compatibilityMode = this.escapeHtml(schema.compatibility_mode || 'UNKNOWN');
            const compatibilityBadge = this.getCompatibilityBadge(schema.compatibility_mode);
            
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${subject}</td>
                <td>${environments}</td>
                <td>${owner}</td>
                <td>${compatibilityBadge}</td>
                <td>
                    <div style="display: flex; gap: 0.5rem;">
                        <button class="btn-icon analyze-delete-btn" data-subject="${this.escapeHtml(rawSubject)}" title="Delete impact analysis">
                            <i class="fas fa-exclamation-circle"></i>
                        </button>
                    </div>
                </td>
                <td>
                    <button class="btn-icon btn-danger delete-schema-btn" data-subject="${this.escapeHtml(rawSubject)}" title="스키마 삭제">
                        <i class="fas fa-trash"></i>
                    </button>
                </td>
            `;
            tbody.appendChild(row);
            
            // 이벤트 리스너 연결
            const deleteBtn = row.querySelector('.delete-schema-btn');
            if (deleteBtn && appInstance) {
                deleteBtn.addEventListener('click', () => appInstance.handleSchemaDelete(rawSubject));
            }
        });
    }

    /**
     * 환경별 CSS 클래스
     */
    static getEnvClass(env) {
        const classes = {
            dev: 'success',
            stg: 'warning',
            prod: 'error'
        };
        return classes[env?.toLowerCase()] || 'success';
    }

    /**
     * 상태별 CSS 클래스
     */
    static getStatusClass(status) {
        const classes = {
            active: 'success',
            inactive: 'warning',
            error: 'error'
        };
        return classes[status?.toLowerCase()] || 'success';
    }

    /**
     * 호환성 모드 배지 렌더링
     */
    static getCompatibilityBadge(mode) {
        if (!mode || mode === 'UNKNOWN') {
            return '<span class="badge badge-secondary">UNKNOWN</span>';
        }
        
        const badgeClasses = {
            'NONE': 'badge-secondary',
            'BACKWARD': 'badge-primary',
            'BACKWARD_TRANSITIVE': 'badge-primary',
            'FORWARD': 'badge-info',
            'FORWARD_TRANSITIVE': 'badge-info',
            'FULL': 'badge-success',
            'FULL_TRANSITIVE': 'badge-success',
        };
        
        const badgeClass = badgeClasses[mode] || 'badge-secondary';
        return `<span class="badge ${badgeClass}">${this.escapeHtml(mode)}</span>`;
    }

    /**
     * 히스토리 테이블 렌더링
     */
    static renderHistoryTable(activities) {
        const tbody = document.getElementById('history-table-body');
        tbody.innerHTML = '';

        if (!activities || activities.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="7" style="text-align: center; padding: 2rem; color: var(--text-muted);">
                        No activity history. Try adjusting the filters.
                    </td>
                </tr>
            `;
            return;
        }

        activities.forEach(activity => {
            const timestamp = new Date(activity.timestamp).toLocaleString('ko-KR', {
                year: 'numeric',
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit'
            });
            
            const typeColor = activity.activity_type === 'topic' ? 'primary' : 'info';
            const actionBadge = this.getActionBadge(activity.action);
            const team = activity.team || '-';
            
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${this.escapeHtml(timestamp)}</td>
                <td><span class="status-badge ${typeColor}">${this.escapeHtml(activity.activity_type.toUpperCase())}</span></td>
                <td>${actionBadge}</td>
                <td>${this.escapeHtml(activity.target)}</td>
                <td>${this.escapeHtml(team)}</td>
                <td>${this.escapeHtml(activity.actor || '-')}</td>
                <td>${this.escapeHtml(activity.message || '-')}</td>
            `;
            tbody.appendChild(row);
        });
    }

    /**
     * 액션 배지 생성
     */
    static getActionBadge(action) {
        const badgeClass = {
            CREATE: 'success',
            REGISTER: 'success',
            UPLOAD: 'success',
            UPDATE: 'warning',
            ALTER: 'warning',
            DELETE: 'error',
            DRY_RUN: 'info',
            APPLY: 'success'
        };
        const className = badgeClass[action] || 'info';
        return `<span class="status-badge ${className}">${this.escapeHtml(action)}</span>`;
    }

    /**
     * 태그 색상 클래스 생성 (해시 기반)
     */
    static getTagColorClass(tag) {
        const colors = [
            'blue', 'green', 'yellow', 'red', 'purple',  
            'pink', 'indigo', 'cyan', 'orange', 'gray'
        ];
        
        // 태그 문자열을 해시하여 색상 인덱스 결정
        let hash = 0;
        for (let i = 0; i < tag.length; i++) {
            hash = tag.charCodeAt(i) + ((hash << 5) - hash);
        }
        const colorIndex = Math.abs(hash) % colors.length;
        return `tag-badge-${colors[colorIndex]}`;
    }

    /**
     * 환경별 CSS 클래스
     */
    static getEnvClass(env) {
        const envLower = (env || '').toLowerCase();
        if (envLower === 'prod') return 'error';
        if (envLower === 'stg') return 'warning';
        if (envLower === 'dev') return 'success';
        return '';
    }
}

// =================
// 활동 렌더러
// =================
class ActivityRenderer {
    /**
     * 최근 활동 렌더링
     */
    static renderRecentActivities(activities) {
        const container = document.getElementById('recent-activities') || document.getElementById('recent-activities-list');
        
        if (!activities || activities.length === 0) {
            container.innerHTML = `
                <div style="text-align: center; padding: 2rem; color: var(--text-muted);">
                    No recent activities.
                </div>
            `;
            return;
        }

        container.innerHTML = activities.map(activity => {
            const metadata = activity.metadata || {};
            const method = metadata.method || '';
            const actions = metadata.actions || {};
            
            // 단일/배치 뱃지
            const methodBadge = method 
                ? `<span class="method-badge ${method.toLowerCase()}">${method === 'BATCH' ? 'BATCH' : 'SINGLE'}</span>` 
                : '';
            
            // 팀 정보
            const team = activity.team || '';
            const teamBadge = team ? `<span class="team-badge">${this.escapeHtml(team)}</span>` : '';
            
            // 액션 텍스트 생성
            const actionText = this.getActionText(activity.action);
            const target = activity.target || 'N/A';
            
            // 메시지 생성: "팀명이 토픽명을 생성함"
            let displayMessage = '';
            if (team && target) {
                displayMessage = `<strong>${this.escapeHtml(team)}</strong> ${actionText} <strong>${this.escapeHtml(target)}</strong>`;
            } else if (target) {
                displayMessage = `<strong>${this.escapeHtml(target)}</strong> ${actionText}`;
            } else {
                displayMessage = this.escapeHtml(activity.message || 'N/A');
            }
            
            // 상세 정보 생성
            let detailInfo = '';
            if (Object.keys(actions).length > 0) {
                // 액션별 토픽 목록 표시
                const actionDetails = [];
                for (const [action, topics] of Object.entries(actions)) {
                    if (Array.isArray(topics) && topics.length > 0) {
                        const actionText = this.getActionText(action, metadata);
                        actionDetails.push(`
                            <div class="action-detail">
                                <strong>${topics.length}개 ${actionText}</strong>
                                <br>
                                <small class="topic-list">${this.escapeHtml(topics.join(', '))}</small>
                            </div>
                        `);
                    }
                }
                if (actionDetails.length > 0) {
                    detailInfo = `<div class="details-section">${actionDetails.join('')}</div>`;
                }
            }
            
            // DELETE 액션일 때 delete 클래스 추가
            const actionClass = activity.action === 'DELETE' ? 'delete' : '';
            
            return `
                <div class="activity-item">
                    <div class="activity-icon ${activity.activity_type || activity.type} ${actionClass}">
                        <i class="fas ${this.getActivityIcon(activity.action)}"></i>
                    </div>
                    <div class="activity-content">
                        <p>
                            <span class="activity-type-badge">${activity.activity_type === 'topic' || activity.type === 'topic' ? 'TOPIC' : 'SCHEMA'}</span>
                            ${methodBadge}
                            ${displayMessage}
                        </p>
                        ${detailInfo}
                        <small>${this.formatTime(activity.timestamp)} · ${this.escapeHtml(activity.actor)}</small>
                    </div>
                </div>
            `;
        }).join('');
    }

    /**
     * 활동 액션 텍스트 변환
     */
    static getActionText(action, metadata) {
        const actionMap = {
            'CREATE': 'created',
            'UPDATE': 'updated',
            'DELETE': 'deleted',
            'REGISTER': 'registered',
            'UPLOAD': 'uploaded'
        };
        return actionMap[action] || action;
    }

    /**
     * 정책 위반 렌더링
     */
    static renderViolations(violations) {
        const container = document.getElementById('violations-list');
        
        if (!violations || violations.length === 0) {
            container.innerHTML = `
                <div style="text-align: center; padding: 2rem; color: var(--text-muted);">
                    No policy violations.
                </div>
            `;
            return;
        }

        container.innerHTML = violations.map(violation => `
            <div class="violation-item">
                <div class="violation-header">
                    <div class="violation-title">${violation.target}</div>
                    <div class="violation-severity ${violation.severity.toLowerCase()}">${violation.severity}</div>
                </div>
                <div class="violation-message">${violation.message}</div>
            </div>
        `).join('');
    }

    /**
     * 활동 아이콘 매핑
     */
    static getActivityIcon(action) {
        const icons = {
            // 소문자
            create: 'fa-plus',
            update: 'fa-edit',
            delete: 'fa-times',  // 빨간색 X
            register: 'fa-upload',
            // 대문자 (Backend에서 오는 형식)
            CREATE: 'fa-plus',
            UPDATE: 'fa-edit',
            DELETE: 'fa-times',  // 빨간색 X
            REGISTER: 'fa-upload',
            APPLY: 'fa-check',
            DRY_RUN: 'fa-search',
            // 기타
            violation: 'fa-exclamation',
            policy: 'fa-shield-alt'
        };
        return icons[action] || 'fa-info';
    }

    /**
     * HTML 이스케이프
     */
    static escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * 시간 포맷팅
     */
    static formatTime(timestamp) {
        const now = new Date();
        const time = new Date(timestamp);
        const diff = now - time;
        
        const minutes = Math.floor(diff / 60000);
        const hours = Math.floor(diff / 3600000);
        const days = Math.floor(diff / 86400000);
        
        if (minutes < 1) return 'just now';
        if (minutes < 60) return `${minutes} min ago`;
        if (hours < 24) return `${hours} hr ago`;
        return `${days} days ago`;
    }

    /**
     * 클러스터 상태 렌더링
     */
    static renderClusterStatus(clusterStatus) {
        const container = document.getElementById('env-status');
        
        if (!clusterStatus || !clusterStatus.brokers) {
            container.innerHTML = `
                <div style="text-align: center; padding: 2rem; color: var(--text-muted);">
                    Cannot load cluster info.
                </div>
            `;
            return;
        }

        const brokerCards = clusterStatus.brokers.map(broker => {
            const statusClass = 'online';  // 브로커 상태는 항상 online (metadata에서 가져온 경우)
            const statusIcon = '🟢';
            const controllerBadge = broker.is_controller 
                ? '<span class="status-badge controller">CONTROLLER</span>' 
                : '';
            
            return `
                <div class="broker-card">
                    <div class="broker-header">
                        <div class="broker-title">
                            <strong>Broker ${broker.broker_id}</strong>
                            ${controllerBadge}
                        </div>
                        <span class="status-badge ${statusClass}">${statusIcon} Online</span>
                    </div>
                    <div class="broker-info">
                        <div class="info-item">
                            <i class="fas fa-server"></i>
                            <span>${this.escapeHtml(broker.host)}:${broker.port}</span>
                        </div>
                        <div class="info-item">
                            <i class="fas fa-chart-bar"></i>
                            <span>리더 파티션: <strong>${broker.leader_partition_count}개</strong></span>
                        </div>
                    </div>
                </div>
            `;
        }).join('');

        const summaryHtml = `
            <div class="cluster-summary">
                <div class="summary-item">
                    <i class="fas fa-database"></i>
                    <div>
                        <div class="summary-label">전체 토픽</div>
                        <div class="summary-value">${clusterStatus.total_topics}개</div>
                    </div>
                </div>
                <div class="summary-item">
                    <i class="fas fa-th"></i>
                    <div>
                        <div class="summary-label">전체 파티션</div>
                        <div class="summary-value">${clusterStatus.total_partitions}개</div>
                    </div>
                </div>
                <div class="summary-item">
                    <i class="fas fa-server"></i>
                    <div>
                        <div class="summary-label">브로커</div>
                        <div class="summary-value">${clusterStatus.brokers.length}개</div>
                    </div>
                </div>
            </div>
        `;

        container.innerHTML = summaryHtml + `<div class="broker-grid">${brokerCards}</div>`;
    }
}

// =================
// 폼 유틸리티
// =================
class FormUtils {
    /**
     * 폼 데이터를 객체로 변환
     */
    static formToObject(form) {
        const formData = new FormData(form);
        const data = {};
        
        for (const [key, value] of formData.entries()) {
            // 숫자 필드 자동 변환
            if (form.querySelector(`[name="${key}"]`)?.type === 'number') {
                data[key] = value ? parseInt(value, 10) : null;
            } else {
                data[key] = value;
            }
        }
        
        return data;
    }

    /**
     * 폼 초기화
     */
    static resetForm(formId) {
        const form = document.getElementById(formId);
        if (form) {
            form.reset();
        }
    }

    /**
     * 폼 검증
     */
    static validateForm(formId) {
        const form = document.getElementById(formId);
        if (!form) return false;

        const requiredFields = form.querySelectorAll('[required]');
        let isValid = true;

        requiredFields.forEach(field => {
            if (!field.value.trim()) {
                field.style.borderColor = 'var(--error-color)';
                isValid = false;
            } else {
                field.style.borderColor = 'var(--border-color)';
            }
        });

        return isValid;
    }
}

// =================
// 파일 관리
// =================
class FileManager {
    /**
     * 선택된 파일 목록 렌더링
     */
    static renderSelectedFiles(files, containerId) {
        const container = document.getElementById(containerId);
        container.innerHTML = '';

        Array.from(files).forEach((file, index) => {
            const fileItem = document.createElement('div');
            fileItem.className = 'file-item';
            fileItem.innerHTML = `
                <div class="file-info">
                    <i class="fas fa-file-code file-icon"></i>
                    <div>
                        <div style="font-weight: 500;">${file.name}</div>
                        <div style="font-size: 0.75rem; color: var(--text-muted);">
                            ${this.formatFileSize(file.size)} • ${file.type || 'Unknown'}
                        </div>
                    </div>
                </div>
                <button type="button" class="file-remove" onclick="removeFile(${index})">
                    <i class="fas fa-times"></i>
                </button>
            `;
            container.appendChild(fileItem);
        });
    }

    /**
     * 파일 크기 포맷팅
     */
    static formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    /**
     * 파일 타입 검증
     */
    static validateFileType(file, allowedTypes) {
        const extension = file.name.split('.').pop().toLowerCase();
        return allowedTypes.includes(`.${extension}`);
    }

    /**
     * 파일 크기 검증
     */
    static validateFileSize(file, maxSize) {
        return file.size <= maxSize;
    }
}

// 전역으로 노출
window.Toast = Toast;
window.Loading = Loading;
window.Modal = Modal;
window.TableRenderer = TableRenderer;
window.ActivityRenderer = ActivityRenderer;
window.FormUtils = FormUtils;
window.FileManager = FileManager;
