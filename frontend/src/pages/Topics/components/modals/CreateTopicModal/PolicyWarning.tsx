import { useTranslation } from "react-i18next";
import { Info, Shield } from "lucide-react";
import type { ActivePolicies, Environment } from "../../../Topics.types";

interface PolicyWarningProps {
  environment: Environment;
  policies: ActivePolicies;
  loading: boolean;
}

export function PolicyWarning({ environment, policies, loading }: PolicyWarningProps) {
  const { t } = useTranslation();

  if (loading) {
    return (
      <div className="rounded-lg bg-gray-50 p-4 mb-4">
        <div className="flex items-center gap-2 text-gray-600">
          <Shield className="h-5 w-5 animate-pulse" />
          <span className="text-sm">{t("common.loading")}</span>
        </div>
      </div>
    );
  }

  const hasAnyPolicy = policies.naming || policies.guardrail;

  if (!hasAnyPolicy) {
    return (
      <div className="rounded-lg bg-yellow-50 border border-yellow-200 p-4 mb-4">
        <div className="flex items-start gap-3">
          <Info className="h-5 w-5 text-yellow-600 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="text-sm font-medium text-yellow-800">
              {t("policy.noPolicies")}
            </p>
            <p className="text-xs text-yellow-700 mt-1">
              {environment.toUpperCase()} {t("topic.environment")}
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-lg bg-blue-50 border border-blue-200 p-4 mb-4">
      <div className="flex items-start gap-3">
        <Shield className="h-5 w-5 text-blue-600 flex-shrink-0 mt-0.5" />
        <div className="flex-1">
          <p className="text-sm font-medium text-blue-800 mb-2">
            {t("policy.active")} ({environment.toUpperCase()})
          </p>
          <div className="space-y-1">
            {policies.naming && (
              <p className="text-xs text-blue-700">
                • Naming: {policies.naming.name} (v{policies.naming.version})
              </p>
            )}
            {policies.guardrail && (
              <p className="text-xs text-blue-700">
                • Guardrail: {policies.guardrail.name} (v{policies.guardrail.version})
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
