/**
 * Validation 유틸리티
 */

/**
 * 이메일 형식 검증
 */
export function isValidEmail(email: string): boolean {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
}

/**
 * URL 형식 검증
 */
export function isValidUrl(url: string): boolean {
  try {
    new URL(url);
    return true;
  } catch {
    return false;
  }
}

/**
 * Topic 이름 형식 검증 (일반적인 Kafka naming convention)
 */
export function isValidTopicName(name: string): boolean {
  // 알파벳, 숫자, 점(.), 하이픈(-), 언더스코어(_)만 허용
  const topicNameRegex = /^[a-zA-Z0-9._-]+$/;
  
  if (!topicNameRegex.test(name)) {
    return false;
  }
  
  // 길이 제한 (Kafka 기본: 249자)
  if (name.length > 249) {
    return false;
  }
  
  // 점으로만 구성된 이름 금지 (., .., ... 등)
  if (/^\.+$/.test(name)) {
    return false;
  }
  
  return true;
}

/**
 * JSON 형식 검증
 */
export function isValidJson(str: string): boolean {
  try {
    JSON.parse(str);
    return true;
  } catch {
    return false;
  }
}

/**
 * 숫자 범위 검증
 */
export function isInRange(
  value: number,
  min: number,
  max: number
): boolean {
  return value >= min && value <= max;
}

/**
 * 필수 필드 검증
 */
export function isRequired(value: string | null | undefined): boolean {
  return value !== null && value !== undefined && value.trim() !== '';
}

/**
 * 최소 길이 검증
 */
export function hasMinLength(value: string, minLength: number): boolean {
  return value.length >= minLength;
}

/**
 * 최대 길이 검증
 */
export function hasMaxLength(value: string, maxLength: number): boolean {
  return value.length <= maxLength;
}

/**
 * Replication factor 검증 (1 이상, 브로커 수 이하)
 */
export function isValidReplicationFactor(
  replicationFactor: number,
  brokerCount: number
): { valid: boolean; message?: string } {
  if (replicationFactor < 1) {
    return {
      valid: false,
      message: 'Replication factor는 1 이상이어야 합니다.',
    };
  }
  
  if (replicationFactor > brokerCount) {
    return {
      valid: false,
      message: `Replication factor는 브로커 수(${brokerCount})를 초과할 수 없습니다.`,
    };
  }
  
  return { valid: true };
}

/**
 * Partition 수 검증
 */
export function isValidPartitionCount(partitionCount: number): {
  valid: boolean;
  message?: string;
} {
  if (partitionCount < 1) {
    return {
      valid: false,
      message: 'Partition 수는 1 이상이어야 합니다.',
    };
  }
  
  if (partitionCount > 10000) {
    return {
      valid: false,
      message: 'Partition 수는 10000을 초과할 수 없습니다.',
    };
  }
  
  return { valid: true };
}
