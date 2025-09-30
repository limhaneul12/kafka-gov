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
    /**
     * 토픽 테이블 렌더링
     */
    static renderTopicsTable(topics) {
        const tbody = document.getElementById('topics-table-body');
        tbody.innerHTML = '';

        if (!topics || topics.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="7" style="text-align: center; padding: 2rem; color: var(--text-muted);">
                        토픽이 없습니다.
                    </td>
                </tr>
            `;
            return;
        }

        topics.forEach(topic => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>
                    <div style="font-weight: 500;">${topic.name}</div>
                    <div style="font-size: 0.75rem; color: var(--text-muted);">${topic.description || ''}</div>
                </td>
                <td>
                    <span class="status-badge ${this.getEnvClass(topic.environment)}">${topic.environment.toUpperCase()}</span>
                </td>
                <td>${topic.partitions || '-'}</td>
                <td>${topic.replication_factor || '-'}</td>
                <td>${topic.owner || '-'}</td>
                <td>
                    <span class="status-badge ${this.getStatusClass(topic.status)}">${topic.status || 'ACTIVE'}</span>
                </td>
                <td>
                    <div style="display: flex; gap: 0.5rem;">
                        <button class="btn-icon" onclick="viewTopicDetail('${topic.name}')" title="상세 보기">
                            <i class="fas fa-eye"></i>
                        </button>
                        <button class="btn-icon" onclick="editTopic('${topic.name}')" title="편집">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button class="btn-icon" onclick="deleteTopic('${topic.name}')" title="삭제" style="color: var(--error-color);">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </td>
            `;
            tbody.appendChild(row);
        });
    }

    /**
     * 스키마 테이블 렌더링
     */
    static renderSchemasTable(schemas) {
        const tbody = document.getElementById('schemas-table-body');
        tbody.innerHTML = '';

        if (!schemas || schemas.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="6" style="text-align: center; padding: 2rem; color: var(--text-muted);">
                        스키마가 없습니다.
                    </td>
                </tr>
            `;
            return;
        }

        schemas.forEach(schema => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>
                    <div style="font-weight: 500;">${schema.subject}</div>
                    <div style="font-size: 0.75rem; color: var(--text-muted);">${schema.id || ''}</div>
                </td>
                <td>${schema.version || '-'}</td>
                <td>
                    <span class="status-badge">${schema.schema_type || 'AVRO'}</span>
                </td>
                <td>${schema.compatibility || 'BACKWARD'}</td>
                <td>${schema.registered_at ? new Date(schema.registered_at).toLocaleDateString() : '-'}</td>
                <td>
                    <div style="display: flex; gap: 0.5rem;">
                        <button class="btn-icon" onclick="viewSchemaDetail('${schema.subject}')" title="상세 보기">
                            <i class="fas fa-eye"></i>
                        </button>
                        <button class="btn-icon" onclick="downloadSchema('${schema.subject}')" title="다운로드">
                            <i class="fas fa-download"></i>
                        </button>
                        <button class="btn-icon" onclick="deleteSchema('${schema.subject}')" title="삭제" style="color: var(--error-color);">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </td>
            `;
            tbody.appendChild(row);
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
}

// =================
// 활동 렌더러
// =================
class ActivityRenderer {
    /**
     * 최근 활동 렌더링
     */
    static renderRecentActivities(activities) {
        const container = document.getElementById('recent-activities');
        
        if (!activities || activities.length === 0) {
            container.innerHTML = `
                <div style="text-align: center; padding: 2rem; color: var(--text-muted);">
                    최근 활동이 없습니다.
                </div>
            `;
            return;
        }

        container.innerHTML = activities.map(activity => `
            <div class="activity-item">
                <div class="activity-icon ${activity.type}">
                    <i class="fas ${this.getActivityIcon(activity.action)}"></i>
                </div>
                <div class="activity-content">
                    <p><strong>${activity.target}</strong> ${activity.message}</p>
                    <small>${this.formatTime(activity.timestamp)}</small>
                </div>
            </div>
        `).join('');
    }

    /**
     * 정책 위반 렌더링
     */
    static renderViolations(violations) {
        const container = document.getElementById('violations-list');
        
        if (!violations || violations.length === 0) {
            container.innerHTML = `
                <div style="text-align: center; padding: 2rem; color: var(--text-muted);">
                    정책 위반이 없습니다.
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
            create: 'fa-plus',
            update: 'fa-edit',
            delete: 'fa-trash',
            violation: 'fa-exclamation',
            policy: 'fa-shield-alt'
        };
        return icons[action] || 'fa-info';
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
        
        if (minutes < 1) return '방금 전';
        if (minutes < 60) return `${minutes}분 전`;
        if (hours < 24) return `${hours}시간 전`;
        return `${days}일 전`;
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

// =================
// 통계 업데이트
// =================
class StatsUpdater {
    /**
     * 대시보드 통계 업데이트
     */
    static async updateDashboardStats() {
        try {
            // 각 모듈별 헬스 체크로 통계 수집
            const [topicHealth, schemaHealth] = await Promise.allSettled([
                api.topicHealthCheck(),
                api.schemaHealthCheck()
            ]);

            // 통계 업데이트
            document.getElementById('topic-count').textContent = 
                topicHealth.status === 'fulfilled' ? '12' : '-';
            document.getElementById('schema-count').textContent = 
                schemaHealth.status === 'fulfilled' ? '8' : '-';
            document.getElementById('policy-count').textContent = '6';
            document.getElementById('violation-count').textContent = '2';

        } catch (error) {
            console.error('통계 업데이트 실패:', error);
        }
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
window.StatsUpdater = StatsUpdater;
