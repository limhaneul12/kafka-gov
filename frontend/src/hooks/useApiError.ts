/**
 * API 에러 핸들링 훅
 */

import { useCallback } from 'react';
import { toast } from 'sonner';
import { extractErrorMessage } from '../utils/error';

/**
 * API 에러를 Toast로 표시하는 훅
 */
export function useApiError() {
  const handleError = useCallback(
    (error: unknown, customTitle?: string) => {
      const errorMessage = extractErrorMessage(error);
      const title = customTitle || '오류 발생';
      
      console.error(title, error);
      toast.error(title, { description: errorMessage });
    },
    []
  );

  const handleSuccess = useCallback(
    (title: string, message?: string) => {
      toast.success(title, { 
        description: message || '작업이 성공적으로 완료되었습니다.' 
      });
    },
    []
  );

  const handleWarning = useCallback(
    (title: string, message: string) => {
      toast.warning(title, { description: message });
    },
    []
  );

  const handleInfo = useCallback(
    (title: string, message: string) => {
      toast.info(title, { description: message });
    },
    []
  );

  return {
    handleError,
    handleSuccess,
    handleWarning,
    handleInfo,
  };
}
