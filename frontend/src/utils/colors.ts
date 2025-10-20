/**
 * 색상 유틸리티
 */

/**
 * 문자열을 해시하여 일관된 색상 인덱스 반환
 */
function hashString(str: string): number {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = str.charCodeAt(i) + ((hash << 5) - hash);
  }
  return Math.abs(hash);
}

/**
 * Owner(팀)별 색상 클래스 반환
 */
export function getOwnerColor(owner: string): string {
  // Owner(팀)별 고정 색상
  const ownerColors: Record<string, string> = {
    'team-commerce': 'bg-blue-100 text-blue-800 border-blue-200',
    'team-payment': 'bg-green-100 text-green-800 border-green-200',
    'team-notification': 'bg-purple-100 text-purple-800 border-purple-200',
    'team-platform': 'bg-orange-100 text-orange-800 border-orange-200',
    'team-growth': 'bg-pink-100 text-pink-800 border-pink-200',
  };

  // 정의된 팀이면 고정 색상 사용
  if (ownerColors[owner]) {
    return ownerColors[owner];
  }

  // 없으면 해시 기반 색상
  const colors = [
    'bg-indigo-100 text-indigo-800 border-indigo-200',
    'bg-cyan-100 text-cyan-800 border-cyan-200',
    'bg-teal-100 text-teal-800 border-teal-200',
    'bg-lime-100 text-lime-800 border-lime-200',
    'bg-amber-100 text-amber-800 border-amber-200',
  ];

  const index = hashString(owner) % colors.length;
  return colors[index];
}

/**
 * Tag별 색상 클래스 반환
 */
export function getTagColor(tag: string): string {
  // 태그명을 해시하여 일관된 색상 할당
  const colors = [
    'bg-blue-100 text-blue-800',
    'bg-green-100 text-green-800',
    'bg-purple-100 text-purple-800',
    'bg-pink-100 text-pink-800',
    'bg-yellow-100 text-yellow-800',
    'bg-indigo-100 text-indigo-800',
    'bg-red-100 text-red-800',
    'bg-orange-100 text-orange-800',
  ];

  const index = hashString(tag) % colors.length;
  return colors[index];
}

/**
 * Environment별 색상 클래스 반환
 */
export function getEnvColor(env: string): string {
  const envColors: Record<string, string> = {
    dev: 'bg-blue-100 text-blue-800',
    stg: 'bg-yellow-100 text-yellow-800',
    staging: 'bg-yellow-100 text-yellow-800',
    prod: 'bg-red-100 text-red-800',
    production: 'bg-red-100 text-red-800',
  };

  return envColors[env.toLowerCase()] || 'bg-gray-100 text-gray-800';
}

/**
 * Status별 색상 클래스 반환
 */
export function getStatusColor(
  status: string
): {
  badge: string;
  bg: string;
  text: string;
  border: string;
} {
  const statusColors: Record<
    string,
    { badge: string; bg: string; text: string; border: string }
  > = {
    active: {
      badge: 'bg-green-100 text-green-800',
      bg: 'bg-green-50',
      text: 'text-green-900',
      border: 'border-green-200',
    },
    draft: {
      badge: 'bg-gray-100 text-gray-800',
      bg: 'bg-gray-50',
      text: 'text-gray-900',
      border: 'border-gray-200',
    },
    archived: {
      badge: 'bg-red-100 text-red-800',
      bg: 'bg-red-50',
      text: 'text-red-900',
      border: 'border-red-200',
    },
    running: {
      badge: 'bg-green-100 text-green-800',
      bg: 'bg-green-50',
      text: 'text-green-900',
      border: 'border-green-200',
    },
    paused: {
      badge: 'bg-yellow-100 text-yellow-800',
      bg: 'bg-yellow-50',
      text: 'text-yellow-900',
      border: 'border-yellow-200',
    },
    failed: {
      badge: 'bg-red-100 text-red-800',
      bg: 'bg-red-50',
      text: 'text-red-900',
      border: 'border-red-200',
    },
  };

  return (
    statusColors[status.toLowerCase()] || {
      badge: 'bg-gray-100 text-gray-800',
      bg: 'bg-gray-50',
      text: 'text-gray-900',
      border: 'border-gray-200',
    }
  );
}
