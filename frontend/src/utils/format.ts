/**
 * 포맷팅 유틸리티
 */

/**
 * 날짜 문자열을 로케일 형식으로 포맷
 */
export function formatDate(dateString: string | null | undefined): string {
  if (!dateString) return '-';
  
  try {
    const date = new Date(dateString);
    return date.toLocaleString('ko-KR', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return dateString;
  }
}

/**
 * 날짜를 상대 시간으로 포맷 (예: "3분 전")
 */
export function formatRelativeTime(dateString: string | null | undefined): string {
  if (!dateString) return '-';

  try {
    const date = new Date(dateString);
    const now = new Date();
    const diff = now.getTime() - date.getTime();

    const seconds = Math.floor(diff / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);

    if (days > 7) {
      return formatDate(dateString);
    } else if (days > 0) {
      return `${days}일 전`;
    } else if (hours > 0) {
      return `${hours}시간 전`;
    } else if (minutes > 0) {
      return `${minutes}분 전`;
    } else {
      return '방금 전';
    }
  } catch {
    return dateString;
  }
}

/**
 * 바이트를 사람이 읽기 쉬운 형식으로 변환
 */
export function formatBytes(bytes: number | null | undefined): string {
  if (bytes === null || bytes === undefined) return '-';
  if (bytes === 0) return '0 Bytes';

  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));

  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
}

/**
 * 숫자를 천 단위 구분 기호와 함께 포맷
 */
export function formatNumber(num: number | null | undefined): string {
  if (num === null || num === undefined) return '-';
  return num.toLocaleString('ko-KR');
}

/**
 * 밀리초를 사람이 읽기 쉬운 기간으로 변환
 */
export function formatDuration(ms: number | null | undefined): string {
  if (ms === null || ms === undefined) return '-';

  const seconds = Math.floor(ms / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);

  if (days > 0) {
    return `${days}일`;
  } else if (hours > 0) {
    return `${hours}시간`;
  } else if (minutes > 0) {
    return `${minutes}분`;
  } else {
    return `${seconds}초`;
  }
}

/**
 * Retention (ms)을 읽기 쉬운 형식으로 변환
 */
export function formatRetention(retentionMs: number | null | undefined): string {
  if (retentionMs === null || retentionMs === undefined) return '-';
  
  const days = retentionMs / (1000 * 60 * 60 * 24);
  
  if (days >= 365) {
    return `${Math.floor(days / 365)}년`;
  } else if (days >= 30) {
    return `${Math.floor(days / 30)}개월`;
  } else if (days >= 7) {
    return `${Math.floor(days / 7)}주`;
  } else if (days >= 1) {
    return `${days}일`;
  } else {
    return formatDuration(retentionMs);
  }
}

/**
 * 퍼센트 포맷
 */
export function formatPercent(value: number | null | undefined, decimals = 1): string {
  if (value === null || value === undefined) return '-';
  return `${value.toFixed(decimals)}%`;
}

/**
 * Topic 이름을 축약 (너무 길 경우)
 */
export function truncateTopicName(name: string, maxLength = 50): string {
  if (name.length <= maxLength) return name;
  
  const parts = name.split('.');
  if (parts.length <= 2) {
    return `${name.substring(0, maxLength - 3)}...`;
  }
  
  // 처음과 끝 유지하고 중간 축약
  const first = parts[0];
  const last = parts[parts.length - 1];
  return `${first}...${last}`;
}
