import Button from "../ui/Button";
import { X, FileJson, FileText } from "lucide-react";
import { downloadJSON, downloadText } from "../../utils/download";

interface SuccessReportModalProps {
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
      }>;
      summary: Record<string, number>;
    };
  }>;
}

export default function SuccessReportModal({
  isOpen,
  onClose,
  results,
}: SuccessReportModalProps) {
  if (!isOpen) return null;

  const totalSuccess = results.filter(r => r.success).length;
  const totalApplied = results.reduce((sum, r) => sum + (r.response?.applied?.length || 0), 0);
  const totalSkipped = results.reduce((sum, r) => sum + (r.response?.skipped?.length || 0), 0);
  const totalFailed = results.reduce((sum, r) => sum + (r.response?.failed?.length || 0), 0);

  const reportText = `
═══════════════════════════════════════
  토픽 배치 처리 성공 리포트
═══════════════════════════════════════

📊 요약
─────────────────────────────────────
• 배치 성공: ${totalSuccess}개
• 토픽 생성/수정: ${totalApplied}개
• 토픽 스킵: ${totalSkipped}개
• 토픽 실패: ${totalFailed}개

═══════════════════════════════════════
  상세 내역
═══════════════════════════════════════

${results.map((result, index) => {
  if (result.success && result.response) {
    return `
[배치 ${index + 1}]
환경: ${result.response.env}
Change ID: ${result.response.change_id}

✓ 생성/수정된 토픽 (${result.response.applied.length}개):
${result.response.applied.map((name, i) => `  ${i + 1}. ${name}`).join('\n')}

${result.response.skipped && result.response.skipped.length > 0 ? `
⊘ 스킵된 토픽 (${result.response.skipped.length}개):
${result.response.skipped.map((name, i) => `  ${i + 1}. ${name}`).join('\n')}
` : ''}
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
    downloadText(reportText, `topic-success-report-${timestamp}.txt`);
  };

  const handleDownloadJSON = () => {
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    downloadJSON({
      timestamp: new Date().toISOString(),
      summary: {
        totalBatches: results.length,
        successBatches: totalSuccess,
        appliedTopics: totalApplied,
        skippedTopics: totalSkipped,
        failedTopics: totalFailed,
      },
      details: results.filter(r => r.success).map((r, index) => ({
        batchIndex: index + 1,
        environment: r.response?.env,
        changeId: r.response?.change_id,
        applied: r.response?.applied,
        skipped: r.response?.skipped,
      })),
    }, `topic-success-report-${timestamp}.json`);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 p-4">
      <div className="w-full max-w-3xl my-8 rounded-lg bg-white p-6 shadow-xl max-h-[85vh] flex flex-col">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-2xl font-bold text-gray-900">
            배치 처리 성공 리포트
          </h2>
          <button
            onClick={onClose}
            className="rounded-lg p-2 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Summary */}
        <div className="mb-4 grid grid-cols-4 gap-2">
          <div className="bg-blue-50 border border-blue-200 rounded p-3 text-center">
            <div className="text-2xl font-bold text-blue-900">{totalSuccess}</div>
            <div className="text-xs text-blue-700">배치 성공</div>
          </div>
          <div className="bg-green-50 border border-green-200 rounded p-3 text-center">
            <div className="text-2xl font-bold text-green-900">{totalApplied}</div>
            <div className="text-xs text-green-700">생성/수정</div>
          </div>
          <div className="bg-gray-50 border border-gray-200 rounded p-3 text-center">
            <div className="text-2xl font-bold text-gray-900">{totalSkipped}</div>
            <div className="text-xs text-gray-700">스킵</div>
          </div>
          <div className="bg-orange-50 border border-orange-200 rounded p-3 text-center">
            <div className="text-2xl font-bold text-orange-900">{totalFailed}</div>
            <div className="text-xs text-orange-700">실패</div>
          </div>
        </div>

        {/* Details */}
        <div className="flex-1 overflow-y-auto bg-gray-50 rounded-lg p-4 border border-gray-200">
          <h3 className="font-semibold text-gray-900 mb-3">처리 상세</h3>
          <div className="space-y-4">
            {results.map((result, index) => {
              if (result.success && result.response) {
                return (
                  <div key={index} className="bg-white rounded-lg border border-green-200 p-4">
                    <div className="flex items-center gap-2 mb-3">
                      <span className="px-2 py-1 bg-green-100 text-green-800 text-xs font-medium rounded">
                        배치 {index + 1}
                      </span>
                      <span className="text-sm text-gray-600">
                        {result.response.env} | {result.response.change_id}
                      </span>
                    </div>
                    
                    {result.response.applied.length > 0 && (
                      <div className="mb-3">
                        <div className="text-sm font-medium text-green-900 mb-2">
                          ✓ 생성/수정된 토픽 ({result.response.applied.length}개)
                        </div>
                        <div className="grid grid-cols-2 gap-2">
                          {result.response.applied.slice(0, 10).map((name, i) => (
                            <div key={i} className="text-xs text-gray-700 bg-green-50 px-2 py-1 rounded">
                              {i + 1}. {name}
                            </div>
                          ))}
                          {result.response.applied.length > 10 && (
                            <div className="text-xs text-gray-500 italic col-span-2">
                              ... 외 {result.response.applied.length - 10}개
                            </div>
                          )}
                        </div>
                      </div>
                    )}

                    {result.response.skipped && result.response.skipped.length > 0 && (
                      <div>
                        <div className="text-sm font-medium text-gray-700 mb-2">
                          ⊘ 스킵된 토픽 ({result.response.skipped.length}개)
                        </div>
                        <div className="grid grid-cols-2 gap-2">
                          {result.response.skipped.slice(0, 5).map((name, i) => (
                            <div key={i} className="text-xs text-gray-600 bg-gray-50 px-2 py-1 rounded">
                              {i + 1}. {name}
                            </div>
                          ))}
                          {result.response.skipped.length > 5 && (
                            <div className="text-xs text-gray-500 italic col-span-2">
                              ... 외 {result.response.skipped.length - 5}개
                            </div>
                          )}
                        </div>
                      </div>
                    )}
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
