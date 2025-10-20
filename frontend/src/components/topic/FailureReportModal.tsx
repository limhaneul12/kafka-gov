import Button from "../ui/Button";
import { X, FileJson, FileText } from "lucide-react";
import { downloadJSON, downloadText } from "../../utils/download";

interface FailureReportModalProps {
  isOpen: boolean;
  onClose: () => void;
  results: Array<{
    success: boolean;
    doc: string;
    response?: {
      env: string;
      change_id: string;
      applied: string[];
      skipped?: string[];
      failed: Array<{
        topic_name: string | null;
        failure_type: string;
        error_message: string;
        suggestions: string[];
        violations?: Array<{ rule: string; message: string }>;
        raw_error?: string;  // 원본 에러 (디버깅용)
      }>;
      summary: Record<string, number>;
    };
  }>;
}

export default function FailureReportModal({
  isOpen,
  onClose,
  results,
}: FailureReportModalProps) {
  if (!isOpen) return null;

  const totalSuccess = results.filter(r => r.success).length;
  const totalFail = results.filter(r => !r.success).length;
  const totalApplied = results.reduce((sum, r) => sum + (r.response?.applied?.length || 0), 0);
  const totalSkipped = results.reduce((sum, r) => sum + (r.response?.skipped?.length || 0), 0);
  const totalFailed = results.reduce((sum, r) => sum + (r.response?.failed?.length || 0), 0);

  const reportText = `
═══════════════════════════════════════
  토픽 배치 처리 실패 리포트
═══════════════════════════════════════

📊 요약
─────────────────────────────────────
• 배치 성공: ${totalSuccess}개
• 배치 실패: ${totalFail}개
• 토픽 생성/수정: ${totalApplied}개
• 토픽 스킵: ${totalSkipped}개
• 토픽 실패: ${totalFailed}개

═══════════════════════════════════════
  실패 상세
═══════════════════════════════════════

${results.map((result, index) => {
  if (!result.success && result.response?.failed) {
    return `
[배치 ${index + 1}]
환경: ${result.response.env}
Change ID: ${result.response.change_id}

${result.response.failed.map((fail, failIndex) => `
  ${failIndex + 1}. ${fail.topic_name || '(파싱 실패)'}
     ├─ 실패 타입: ${fail.failure_type}
     ├─ 에러 메시지: ${fail.error_message}
     ${fail.violations && fail.violations.length > 0 ? `├─ 정책 위반:\n${fail.violations.map(v => `     │  • ${v.rule}: ${v.message}`).join('\n')}` : ''}
     └─ 제안사항:\n${fail.suggestions.map(s => `        • ${s}`).join('\n')}
`).join('\n')}
`;
  }
  return '';
}).filter(Boolean).join('\n')}

═══════════════════════════════════════
  생성 일시: ${new Date().toLocaleString('ko-KR')}
═══════════════════════════════════════
`.trim();

  const handleDownloadText = () => {
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    downloadText(reportText, `topic-failure-report-${timestamp}.txt`);
  };

  const handleDownloadJSON = () => {
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    downloadJSON({
      timestamp: new Date().toISOString(),
      summary: {
        totalBatches: results.length,
        successBatches: totalSuccess,
        failedBatches: totalFail,
        appliedTopics: totalApplied,
        skippedTopics: totalSkipped,
        failedTopics: totalFailed,
      },
      failures: results.filter(r => !r.success).map((r, index) => ({
        batchIndex: index + 1,
        environment: r.response?.env,
        changeId: r.response?.change_id,
        failed: r.response?.failed,
      })),
    }, `topic-failure-report-${timestamp}.json`);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 p-4">
      <div className="w-full max-w-3xl my-8 rounded-lg bg-white p-6 shadow-xl max-h-[85vh] flex flex-col">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-2xl font-bold text-gray-900">
            배치 처리 실패 리포트
          </h2>
          <button
            onClick={onClose}
            className="rounded-lg p-2 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Summary */}
        <div className="mb-4 grid grid-cols-3 gap-2">
          <div className="bg-blue-50 border border-blue-200 rounded p-3 text-center">
            <div className="text-2xl font-bold text-blue-900">{totalSuccess}</div>
            <div className="text-xs text-blue-700">배치 성공</div>
          </div>
          <div className="bg-red-50 border border-red-200 rounded p-3 text-center">
            <div className="text-2xl font-bold text-red-900">{totalFail}</div>
            <div className="text-xs text-red-700">배치 실패</div>
          </div>
          <div className="bg-green-50 border border-green-200 rounded p-3 text-center">
            <div className="text-2xl font-bold text-green-900">{totalApplied}</div>
            <div className="text-xs text-green-700">생성/수정</div>
          </div>
        </div>

        {/* Failure Details */}
        <div className="flex-1 overflow-y-auto bg-gray-50 rounded-lg p-4 border border-gray-200">
          <h3 className="font-semibold text-gray-900 mb-3">실패 상세</h3>
          <div className="space-y-4">
            {results.map((result, index) => {
              if (!result.success) {
                return (
                  <div key={index} className="bg-white rounded-lg border border-red-200 p-4">
                    <div className="flex items-center gap-2 mb-3">
                      <span className="px-2 py-1 bg-red-100 text-red-800 text-xs font-medium rounded">
                        배치 {index + 1}
                      </span>
                      {result.response && (
                        <span className="text-sm text-gray-600">
                          {result.response.env} | {result.response.change_id}
                        </span>
                      )}
                    </div>
                    <div className="space-y-3">
                      {result.response?.failed && result.response.failed.length > 0 ? (
                        result.response.failed.map((fail, failIndex) => (
                          <div key={failIndex} className="border-l-4 border-red-400 pl-3">
                            <div className="font-medium text-gray-900">
                              {fail.topic_name || '(파싱 실패)'}
                            </div>
                            <div className="text-sm text-gray-600 mt-1">
                              <span className="font-medium">타입:</span> {fail.failure_type}
                            </div>
                            <div className="text-sm text-red-700 mt-2 bg-red-50 border border-red-200 rounded p-3">
                              <div className="font-semibold mb-1">⚠️ 에러 내용:</div>
                              <div className="whitespace-pre-wrap font-mono text-xs">
                                {fail.error_message}
                              </div>
                            </div>
                            {fail.raw_error && (
                              <details className="mt-2">
                                <summary className="cursor-pointer text-xs text-gray-500 hover:text-gray-700">
                                  🔍 상세 에러 보기 (디버깅용)
                                </summary>
                                <pre className="mt-1 p-2 bg-gray-100 rounded text-xs text-gray-800 overflow-x-auto whitespace-pre-wrap">
                                  {fail.raw_error}
                                </pre>
                              </details>
                            )}
                            {fail.violations && fail.violations.length > 0 && (
                              <div className="mt-2 bg-yellow-50 border border-yellow-200 rounded p-2">
                                <div className="text-xs font-medium text-yellow-900 mb-1">
                                  정책 위반:
                                </div>
                                {fail.violations.map((v, vIndex) => (
                                  <div key={vIndex} className="text-xs text-yellow-800">
                                    • {v.rule}: {v.message}
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>
                        ))
                      ) : result.response?.failed && result.response.failed.length > 0 ? (
                        // response.failed가 있지만 렌더링되지 않은 경우 (일반적으로 발생하지 않음)
                        <div className="border-l-4 border-red-400 pl-3">
                          <div className="font-medium text-gray-900">⚠️ 예상치 못한 오류</div>
                          <div className="text-sm text-red-700 bg-red-50 border border-red-200 rounded p-3 mt-2">
                            <div className="font-semibold mb-1">에러 내용:</div>
                            <div className="whitespace-pre-wrap">
                              {result.response.failed[0]?.error_message || 'Unknown error'}
                            </div>
                          </div>
                          {result.response.failed[0]?.raw_error && (
                            <details className="mt-2">
                              <summary className="cursor-pointer text-xs text-gray-500 hover:text-gray-700">
                                🔍 상세 에러 보기 (디버깅용)
                              </summary>
                              <pre className="mt-1 p-2 bg-gray-100 rounded text-xs text-gray-800 overflow-x-auto whitespace-pre-wrap">
                                {result.response.failed[0].raw_error}
                              </pre>
                            </details>
                          )}
                        </div>
                      ) : (
                        // 완전히 알 수 없는 오류
                        <div className="border-l-4 border-red-400 pl-3">
                          <div className="font-medium text-gray-900">⚠️ 배치 처리 실패</div>
                          <div className="text-sm text-red-700 bg-red-50 border border-red-200 rounded p-3 mt-2">
                            <div className="font-semibold mb-1">에러 내용:</div>
                            <div>응답 파싱 실패. 브라우저 콘솔(F12)에서 상세 에러를 확인하세요.</div>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                );
              }
              return null;
            })}
          </div>
        </div>

        {/* Actions */}
        <div className="flex justify-end gap-2 pt-4 mt-4 border-t border-gray-200">
          <Button variant="secondary" onClick={handleDownloadText}>
            <FileText className="h-4 w-4" />
            텍스트 다운로드
          </Button>
          <Button variant="secondary" onClick={handleDownloadJSON}>
            <FileJson className="h-4 w-4" />
            JSON 다운로드
          </Button>
          <Button onClick={onClose}>
            닫기
          </Button>
        </div>
      </div>
    </div>
  );
}
