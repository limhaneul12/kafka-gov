import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { Shield } from "lucide-react";

import Button from "../components/ui/Button";
import Badge from "../components/ui/Badge";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/Card";
import { cn } from "../utils/cn";
import {
  incidentPolicyLibrary,
  type IncidentPolicyStatus,
} from "./incidentPoliciesData";

type BadgeVariant = "default" | "success" | "warning" | "danger" | "info";

const statusBadgeVariant: Record<IncidentPolicyStatus, BadgeVariant> = {
  draft: "warning",
  active: "success",
  archived: "default",
};

export default function IncidentPolicies() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [activeState, setActiveState] = useState<Record<string, boolean>>(() =>
    Object.fromEntries(incidentPolicyLibrary.map((policy) => [policy.id, policy.active]))
  );

  const handleToggleActive = (policyId: string) => {
    setActiveState((prev) => ({
      ...prev,
      [policyId]: !prev[policyId],
    }));
  };

  const handleRowClick = (policyId: string) => {
    navigate(`/policies/incidents/${policyId}`);
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
          <h1 className="text-2xl font-bold">{t("incidentPolicy.list.title")}</h1>
          <p className="text-sm text-gray-500">{t("incidentPolicy.list.description")}</p>
        </div>
        <Button variant="secondary" className="gap-2" disabled>
          {t("incidentPolicy.list.create")}
        </Button>
      </div>

      <Card>
        <CardHeader className="flex items-center justify-between">
          <CardTitle className="text-base">
            {t("incidentPolicy.list.tableTitle")}
          </CardTitle>
          <Button variant="ghost" size="sm" disabled>
            {t("incidentPolicy.list.tableFilter")}
          </Button>
        </CardHeader>
        <CardContent className="p-0">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50 text-xs uppercase tracking-wide text-gray-500">
              <tr>
                <th scope="col" className="px-6 py-3 text-left">
                  {t("incidentPolicy.list.columns.id")}
                </th>
                <th scope="col" className="px-6 py-3 text-left">
                  {t("incidentPolicy.list.columns.name")}
                </th>
                <th scope="col" className="px-6 py-3 text-left">
                  {t("incidentPolicy.list.columns.validPeriod")}
                </th>
                <th scope="col" className="px-6 py-3 text-left">
                  {t("incidentPolicy.list.columns.createdAt")}
                </th>
                <th scope="col" className="px-6 py-3 text-left">
                  {t("incidentPolicy.list.columns.createdBy")}
                </th>
                <th scope="col" className="px-6 py-3 text-right">
                  {t("incidentPolicy.list.columns.status")}
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {incidentPolicyLibrary.map((policy) => {
                const isActive = Boolean(activeState[policy.id]);
                return (
                  <tr
                    key={policy.id}
                    className="cursor-pointer transition-colors hover:bg-blue-50/40"
                    onClick={() => handleRowClick(policy.id)}
                  >
                    <td className="px-6 py-4 font-mono text-xs text-gray-500">
                      {policy.id}
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex flex-col gap-1">
                        <span className="font-medium text-gray-900">{policy.name}</span>
                        <span className="text-xs text-gray-500">{policy.description}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-gray-600">{policy.validPeriod}</td>
                    <td className="px-6 py-4 text-gray-600">{policy.createdAt}</td>
                    <td className="px-6 py-4 text-gray-600">@{policy.createdBy}</td>
                    <td className="px-6 py-4">
                      <div className="flex items-center justify-end gap-3">
                        <Badge variant={statusBadgeVariant[policy.status]}>
                          {t(`incidentPolicy.list.status.${policy.status}`)}
                        </Badge>
                        <button
                          type="button"
                          className={cn(
                            "relative inline-flex h-6 w-12 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2",
                            isActive ? "bg-blue-600" : "bg-gray-300",
                          )}
                          onClick={(event) => {
                            event.stopPropagation();
                            handleToggleActive(policy.id);
                          }}
                        >
                          <span
                            className={cn(
                              "inline-block h-5 w-5 transform rounded-full bg-white shadow transition-transform",
                              isActive ? "translate-x-6" : "translate-x-1",
                            )}
                          />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {incidentPolicyLibrary.length === 0 ? (
            <div className="px-6 py-12 text-center text-sm text-gray-500">
              {t("incidentPolicy.list.empty")}
            </div>
          ) : null}
        </CardContent>
      </Card>
    </div>
  );
}
