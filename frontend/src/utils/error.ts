/**
 * API 에러 처리 유틸리티
 */

/**
 * Axios 에러에서 상세 메시지 추출
 */
export function extractErrorMessage(error: unknown): string {
  // 기본 에러 메시지
  let errorMessage = '알 수 없는 오류가 발생했습니다.';

  // Axios 에러 응답 파싱
  if (error && typeof error === 'object' && 'response' in error) {
    const axiosError = error as {
      response?: {
        data?: {
          detail?: string | Array<{ msg: string; type?: string }>;
          message?: string;
        };
      };
    };

    const detail = axiosError.response?.data?.detail;
    const message = axiosError.response?.data?.message;

    if (detail) {
      if (typeof detail === 'string') {
        errorMessage = detail;
      } else if (Array.isArray(detail)) {
        // Pydantic validation errors
        errorMessage = detail.map(e => e.msg).join(', ');
      }
    } else if (message) {
      errorMessage = message;
    }
  } else if (error instanceof Error) {
    errorMessage = error.message;
  }

  return errorMessage;
}

/**
 * Axios 에러에서 Backend 응답 데이터 추출
 */
export function extractErrorData<T = unknown>(error: unknown): T | null {
  if (error && typeof error === 'object' && 'response' in error) {
    const axiosError = error as { response?: { data?: T } };
    return axiosError.response?.data || null;
  }
  return null;
}

/**
 * HTTP 상태 코드 확인
 */
export function isHttpError(error: unknown, statusCode: number): boolean {
  if (error && typeof error === 'object' && 'response' in error) {
    const axiosError = error as { response?: { status?: number } };
    return axiosError.response?.status === statusCode;
  }
  return false;
}

/**
 * 네트워크 에러 확인
 */
export function isNetworkError(error: unknown): boolean {
  if (error && typeof error === 'object' && 'code' in error) {
    const networkError = error as { code?: string };
    return networkError.code === 'ECONNABORTED' || networkError.code === 'ERR_NETWORK';
  }
  return false;
}
