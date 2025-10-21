import { useTranslation } from "react-i18next";
import { CheckCircle2, AlertTriangle, XCircle, Info } from "lucide-react";
import type { DryRunResult as DryRunResultType } from "../../../Topics.types";

interface DryRunResultProps {
  result: DryRunResultType | null;
  onClose: () => void;
}

export function DryRunResult({ result, onClose }: DryRunResultProps) {
  const { t } = useTranslation();

  if (!result) return null;

  const hasViolations = result.violations && result.violations.length > 0;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[80vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className={`px-6 py-4 border-b ${
          result.success && !hasViolations
            ? "bg-green-50 border-green-200"
            : "bg-yellow-50 border-yellow-200"
        }`}>
          <div className="flex items-center gap-3">
            {result.success && !hasViolations ? (
              <CheckCircle2 className="h-6 w-6 text-green-600" />
            ) : (
              <AlertTriangle className="h-6 w-6 text-yellow-600" />
            )}
            <h3 className="text-lg font-semibold text-gray-900">
              Dry-Run Result
            </h3>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {/* Success Message */}
          {result.success && !hasViolations && (
            <div className="rounded-lg bg-green-50 border border-green-200 p-4">
              <div className="flex items-start gap-3">
                <CheckCircle2 className="h-5 w-5 text-green-600 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm font-medium text-green-800">
                    ✅ Validation Passed
                  </p>
                  <p className="text-xs text-green-700 mt-1">
                    All topics passed policy validation. Ready to create!
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Violations */}
          {hasViolations && (
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <XCircle className="h-5 w-5 text-red-600" />
                <h4 className="text-sm font-semibold text-gray-900">
                  Policy Violations ({result.violations.length})
                </h4>
              </div>
              
              {result.violations.map((violation, index) => (
                <div
                  key={index}
                  className="rounded-lg bg-red-50 border border-red-200 p-4"
                >
                  <div className="flex items-start gap-3">
                    <AlertTriangle className="h-5 w-5 text-red-600 flex-shrink-0 mt-0.5" />
                    <div className="flex-1">
                      <p className="text-sm font-medium text-red-800">
                        {violation.rule}
                      </p>
                      <p className="text-xs text-red-700 mt-1">
                        {violation.message}
                      </p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Preview */}
          {result.preview && (
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <Info className="h-5 w-5 text-blue-600" />
                <h4 className="text-sm font-semibold text-gray-900">
                  Preview
                </h4>
              </div>
              
              <div className="rounded-lg bg-gray-50 p-4 font-mono text-xs overflow-x-auto">
                <pre className="text-gray-700">
                  {JSON.stringify(result.preview, null, 2)}
                </pre>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t bg-gray-50 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors"
          >
            {t("common.close")}
          </button>
        </div>
      </div>
    </div>
  );
}
