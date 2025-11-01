import { useTranslation } from "react-i18next";
import { useState } from "react";
import { Shield } from "lucide-react";

import Button from "../components/ui/Button";
import { cn } from "../utils/cn";

interface IncidentPolicyItem {
  id: string;
  name: string;
  duration: string;
  enabled: boolean;
  createdAt: string;
  updatedAt: string;
}

const initialPolicies: IncidentPolicyItem[] = [
  {
    id: "INC-001",
    name: "Critical partition freeze",
    duration: "15m",
    enabled: true,
    createdAt: "2025-09-22",
    updatedAt: "2025-10-12",
  },
  {
    id: "INC-002",
    name: "High-lag throttle",
    duration: "1h",
    enabled: false,
    createdAt: "2025-10-01",
    updatedAt: "2025-10-05",
  },
];

export default function IncidentPolicies() {
  const { t } = useTranslation();
  const [policies, setPolicies] = useState<IncidentPolicyItem[]>(initialPolicies);

  const togglePolicy = (id: string) => {
    setPolicies((prev) =>
      prev.map((policy) =>
        policy.id === id ? { ...policy, enabled: !policy.enabled } : policy,
      ),
    );
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-blue-600">
            <Shield className="h-5 w-5" />
            <span className="text-sm font-semibold uppercase tracking-wide">
              {t("nav.policyIncident")}
            </span>
          </div>
          <h1 className="text-2xl font-bold">{t("incidentPolicy.title")}</h1>
          <p className="text-sm text-gray-500">{t("incidentPolicy.description")}</p>
        </div>
        <Button variant="secondary" disabled>
          {t("incidentPolicy.addPolicy")}
        </Button>
      </div>

      <div className="overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                {t("incidentPolicy.columns.enabled")}
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                {t("incidentPolicy.columns.id")}
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                {t("incidentPolicy.columns.name")}
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                {t("incidentPolicy.columns.duration")}
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                {t("incidentPolicy.columns.createdAt")}
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                {t("incidentPolicy.columns.updatedAt")}
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                {t("incidentPolicy.actions")}
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {policies.map((policy) => (
              <tr key={policy.id} className="hover:bg-gray-50">
                <td className="px-6 py-4">
                  <div className="flex items-center gap-3">
                    <button
                      type="button"
                      onClick={() => togglePolicy(policy.id)}
                      className={cn(
                        "relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2",
                        policy.enabled ? "bg-green-500" : "bg-gray-300",
                      )}
                    >
                      <span
                        className={cn(
                          "inline-block h-5 w-5 transform rounded-full bg-white shadow transition-transform",
                          policy.enabled ? "translate-x-5" : "translate-x-1",
                        )}
                      />
                    </button>
                    <span className="text-sm font-medium text-gray-700">
                      {policy.enabled ? t("incidentPolicy.toggleOn") : t("incidentPolicy.toggleOff")}
                    </span>
                  </div>
                </td>
                <td className="px-6 py-4 text-sm text-gray-600">{policy.id}</td>
                <td className="px-6 py-4 text-sm font-medium text-gray-900">{policy.name}</td>
                <td className="px-6 py-4 text-sm text-gray-600">{policy.duration}</td>
                <td className="px-6 py-4 text-sm text-gray-600">{policy.createdAt}</td>
                <td className="px-6 py-4 text-sm text-gray-600">{policy.updatedAt}</td>
                <td className="px-6 py-4 text-right text-sm text-gray-500">
                  —
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="text-xs text-gray-500">
        ※ Backend API 연동 전까지는 데모 데이터로 표시됩니다.
      </p>
    </div>
  );
}
