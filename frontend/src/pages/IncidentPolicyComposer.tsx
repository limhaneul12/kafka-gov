import { useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  ArrowLeft,
  Copy,
  Layers3,
  Plus,
  Save,
  Trash2,
} from "lucide-react";
import { toast } from "sonner";

import Button from "../components/ui/Button";
import Badge from "../components/ui/Badge";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/Card";
import { cn } from "../utils/cn";
import {
  getIncidentPolicyById,
  type IncidentPolicyCondition,
  type IncidentPolicyDetail,
} from "./incidentPoliciesData";

const METRIC_OPTIONS = [
  "growth.rate_1h",
  "isr_ratio",
  "consumer.lag.max",
  "partition.skew",
  "topic.retention.ms",
];

const COMPARE_TARGET_OPTIONS = [
  { value: "baseline", label: "Baseline" },
  { value: "previous_interval", label: "Previous" },
  { value: "static", label: "Static" },
];

const OPERATOR_OPTIONS = [
  { value: "delta_pct", label: "delta_pct" },
  { value: "absolute", label: "absolute" },
  { value: "zscore", label: "z-score" },
];

const BASELINE_OPTIONS = [
  "Rolling p95",
  "Rolling p90",
  "Static",
  "Peer average",
];

const WINDOW_OPTIONS = ["5m", "10m", "15m", "30m", "1h", "6h", "24h"];
const STAT_OPTIONS = ["p50", "p90", "p95", "max"];

const ENVIRONMENT_OPTIONS = ["prod", "stage", "dev"];
const TIMEZONE_OPTIONS = ["Asia/Seoul", "UTC", "America/Los_Angeles"];
const INTERVAL_OPTIONS = ["5m", "10m", "15m", "30m", "1h"];
const MODE_OPTIONS = [
  { value: "continuous", label: "Continuous" },
  { value: "interval", label: "Interval" },
  { value: "window", label: "Window" },
] as const;

const createCondition = (): IncidentPolicyCondition => ({
  id: `cond-${Math.random().toString(36).slice(2, 8)}-${Date.now()}`,
  metric: METRIC_OPTIONS[0],
  compareTarget: COMPARE_TARGET_OPTIONS[0].value,
  operator: OPERATOR_OPTIONS[0].value,
  deviation: 50,
  baseline: BASELINE_OPTIONS[0],
  window: WINDOW_OPTIONS[3],
  stat: STAT_OPTIONS[2],
});

export default function IncidentPolicyComposer() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { policyId } = useParams();

  const initialPolicy = useMemo(() => {
    if (!policyId) return null;
    return getIncidentPolicyById(policyId) ?? null;
  }, [policyId]);

  const [policy, setPolicy] = useState<IncidentPolicyDetail | null>(() =>
    initialPolicy ? (JSON.parse(JSON.stringify(initialPolicy)) as IncidentPolicyDetail) : null,
  );

  const handleUpdateScope = (key: "environment" | "selector", value: string) => {
    setPolicy((prev) =>
      prev
        ? {
            ...prev,
            scope: {
              ...prev.scope,
              [key]: value,
            },
          }
        : prev,
    );
  };

  const handleScheduleChange = <K extends keyof IncidentPolicyDetail["schedule"]>(
    key: K,
    value: IncidentPolicyDetail["schedule"][K],
  ) => {
    setPolicy((prev) =>
      prev
        ? {
            ...prev,
            schedule: {
              ...prev.schedule,
              [key]: value,
            },
          }
        : prev,
    );
  };

  const handleRateLimitChange = (key: "perMinutes" | "maxAlerts", value: number) => {
    setPolicy((prev) =>
      prev
        ? {
            ...prev,
            schedule: {
              ...prev.schedule,
              rateLimit: {
                ...prev.schedule.rateLimit,
                [key]: value,
              },
            },
          }
        : prev,
    );
  };

  const handleResponseToggle = (key: "slackAlert" | "enforce" | "waiver") => {
    setPolicy((prev) =>
      prev
        ? {
            ...prev,
            response: {
              ...prev.response,
              [key]: !prev.response[key],
            },
          }
        : prev,
    );
  };

  const handleResponseMemoChange = (value: string) => {
    setPolicy((prev) =>
      prev
        ? {
            ...prev,
            response: {
              ...prev.response,
              memo: value,
            },
          }
        : prev,
    );
  };

  const handleResponseSeverityChange = (
    value: IncidentPolicyDetail["response"]["severity"],
  ) => {
    setPolicy((prev) =>
      prev
        ? {
            ...prev,
            response: {
              ...prev.response,
              severity: value,
            },
          }
        : prev,
    );
  };

  const handleResponseTagsChange = (value: string) => {
    const tags = value
      .split(",")
      .map((tag) => tag.trim())
      .filter(Boolean);

    setPolicy((prev) =>
      prev
        ? {
            ...prev,
            response: {
              ...prev.response,
              tags,
            },
          }
        : prev,
    );
  };

  const handleLogicChange = (logic: "AND" | "OR") => {
    setPolicy((prev) =>
      prev
        ? {
            ...prev,
            rule: {
              ...prev.rule,
              logic,
            },
          }
        : prev,
    );
  };

  const handleConditionChange = <K extends keyof IncidentPolicyCondition>(
    conditionId: string,
    key: K,
    value: IncidentPolicyCondition[K],
  ) => {
    setPolicy((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        rule: {
          ...prev.rule,
          conditions: prev.rule.conditions.map((condition) =>
            condition.id === conditionId ? { ...condition, [key]: value } : condition,
          ),
        },
      };
    });
  };

  const handleAddCondition = () => {
    setPolicy((prev) =>
      prev
        ? {
            ...prev,
            rule: {
              ...prev.rule,
              conditions: [...prev.rule.conditions, createCondition()],
            },
          }
        : prev,
    );
  };

  const handleRemoveCondition = (conditionId: string) => {
    setPolicy((prev) => {
      if (!prev) return prev;
      if (prev.rule.conditions.length <= 1) {
        toast.warning(t("incidentPolicy.ruleEditor.minCondition"));
        return prev;
      }

      return {
        ...prev,
        rule: {
          ...prev.rule,
          conditions: prev.rule.conditions.filter((condition) => condition.id !== conditionId),
        },
      };
    });
  };

  const handleCopyJson = async () => {
    if (!policy) return;
    try {
      if (!navigator.clipboard || !navigator.clipboard.writeText) {
        toast.error(t("incidentPolicy.composer.preview.copyError"));
        return;
      }

      const payload = {
        id: policy.id,
        name: policy.name,
        scope: policy.scope,
        schedule: policy.schedule,
        rule: policy.rule,
        response: policy.response,
      };

      await navigator.clipboard.writeText(JSON.stringify(payload, null, 2));
      toast.success(t("incidentPolicy.composer.preview.copySuccess"));
    } catch (error) {
      console.error(error);
      toast.error(t("incidentPolicy.composer.preview.copyError"));
    }
  };

  const handleSaveDraft = () => {
    toast.success(t("incidentPolicy.composer.actions.saveDraft"));
  };

  const handlePublishMock = () => {
    toast.info(t("incidentPolicy.composer.actions.publishMock"));
  };

  const rulePreview = useMemo(() => {
    if (!policy) return "";
    if (!policy.rule.conditions.length) {
      return t("incidentPolicy.ruleEditor.emptyPlaceholder");
    }

    const conditionStrings = policy.rule.conditions.map((condition) => {
      const metricLabel = condition.metric;
      const operatorLabel = condition.operator;
      const baselineLabel = condition.baseline;
      return `(${metricLabel} ${operatorLabel} ${condition.deviation} → ${baselineLabel})`;
    });

    return conditionStrings.join(` ${policy.rule.logic} `);
  }, [policy, t]);

  const jsonPreview = useMemo(() => {
    if (!policy) return "";
    return JSON.stringify(
      {
        scope: policy.scope,
        schedule: policy.schedule,
        rule: policy.rule,
        response: policy.response,
      },
      null,
      2,
    );
  }, [policy]);

  if (!policy) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-3">
          <Button variant="ghost" onClick={() => navigate("/policies/incidents")}> 
            <ArrowLeft className="h-4 w-4" />
            {t("incidentPolicy.composer.actions.backToList")}
          </Button>
        </div>
        <Card>
          <CardContent className="py-16 text-center text-sm text-gray-500">
            {t("incidentPolicy.composer.notFound")}
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex items-center gap-3">
          <Button variant="ghost" onClick={() => navigate("/policies/incidents")}> 
            <ArrowLeft className="h-4 w-4" />
            {t("incidentPolicy.composer.actions.backToList")}
          </Button>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">
              {t("incidentPolicy.composer.title")}
            </h1>
            <p className="text-sm text-gray-500">
              {t("incidentPolicy.composer.subtitle", { name: policy.name })}
            </p>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Button variant="secondary" className="gap-2" onClick={handleSaveDraft}>
            <Save className="h-4 w-4" />
            {t("incidentPolicy.composer.actions.saveDraft")}
          </Button>
          <Button variant="primary" className="gap-2" onClick={handlePublishMock}>
            <Layers3 className="h-4 w-4" />
            {t("incidentPolicy.composer.actions.publishMock")}
          </Button>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>{t("incidentPolicy.composer.scope.title")}</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-4 md:grid-cols-2">
              <div className="flex flex-col gap-2">
                <label className="text-sm font-medium text-gray-700">
                  {t("incidentPolicy.composer.scope.environment")}
                </label>
                <select
                  value={policy.scope.environment}
                  onChange={(event) => handleUpdateScope("environment", event.target.value)}
                  className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
                >
                  {ENVIRONMENT_OPTIONS.map((env) => (
                    <option key={env} value={env}>
                      {env}
                    </option>
                  ))}
                </select>
              </div>
              <div className="flex flex-col gap-2">
                <label className="text-sm font-medium text-gray-700">
                  {t("incidentPolicy.composer.scope.selector")}
                </label>
                <input
                  type="text"
                  value={policy.scope.selector}
                  onChange={(event) => handleUpdateScope("selector", event.target.value)}
                  className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
                />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>{t("incidentPolicy.composer.schedule.title")}</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-4 md:grid-cols-2">
              <div className="flex flex-col gap-2">
                <label className="text-sm font-medium text-gray-700">
                  {t("incidentPolicy.composer.schedule.mode")}
                </label>
                <select
                  value={policy.schedule.mode}
                  onChange={(event) =>
                    handleScheduleChange(
                      "mode",
                      event.target.value as IncidentPolicyDetail["schedule"]["mode"],
                    )
                  }
                  className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
                >
                  {MODE_OPTIONS.map((mode) => (
                    <option key={mode.value} value={mode.value}>
                      {mode.label}
                    </option>
                  ))}
                </select>
              </div>
              <div className="flex flex-col gap-2">
                <label className="text-sm font-medium text-gray-700">
                  {t("incidentPolicy.composer.schedule.interval")}
                </label>
                <select
                  value={policy.schedule.interval}
                  onChange={(event) =>
                    handleScheduleChange("interval", event.target.value)
                  }
                  className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
                >
                  {INTERVAL_OPTIONS.map((interval) => (
                    <option key={interval} value={interval}>
                      {interval}
                    </option>
                  ))}
                </select>
              </div>
              <div className="flex flex-col gap-2">
                <label className="text-sm font-medium text-gray-700">
                  {t("incidentPolicy.composer.schedule.timezone")}
                </label>
                <select
                  value={policy.schedule.timezone}
                  onChange={(event) =>
                    handleScheduleChange("timezone", event.target.value)
                  }
                  className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
                >
                  {TIMEZONE_OPTIONS.map((timezone) => (
                    <option key={timezone} value={timezone}>
                      {timezone}
                    </option>
                  ))}
                </select>
              </div>
              <div className="flex flex-col gap-2">
                <label className="text-sm font-medium text-gray-700">
                  {t("incidentPolicy.composer.schedule.ttl")}
                </label>
                <input
                  type="datetime-local"
                  value={policy.schedule.ttl ?? ""}
                  onChange={(event) =>
                    handleScheduleChange("ttl", event.target.value || "")
                  }
                  className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
                />
              </div>
              <div className="flex flex-col gap-2">
                <label className="text-sm font-medium text-gray-700">
                  {t("incidentPolicy.composer.schedule.blackout")}
                </label>
                <input
                  type="text"
                  value={policy.schedule.blackout ?? ""}
                  onChange={(event) =>
                    handleScheduleChange("blackout", event.target.value)
                  }
                  placeholder={t("incidentPolicy.composer.schedule.blackoutPlaceholder") ?? ""}
                  className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
                />
              </div>
              <div className="flex flex-col gap-2">
                <label className="text-sm font-medium text-gray-700">
                  {t("incidentPolicy.composer.schedule.rateLimit")}
                </label>
                <div className="grid grid-cols-2 gap-3">
                  <div className="flex flex-col gap-1">
                    <span className="text-xs text-gray-500">
                      {t("incidentPolicy.composer.schedule.perMinutes")}
                    </span>
                    <input
                      type="number"
                      min={0}
                      value={policy.schedule.rateLimit.perMinutes}
                      onChange={(event) =>
                        handleRateLimitChange("perMinutes", Number(event.target.value))
                      }
                      className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
                    />
                  </div>
                  <div className="flex flex-col gap-1">
                    <span className="text-xs text-gray-500">
                      {t("incidentPolicy.composer.schedule.maxAlerts")}
                    </span>
                    <input
                      type="number"
                      min={0}
                      value={policy.schedule.rateLimit.maxAlerts}
                      onChange={(event) =>
                        handleRateLimitChange("maxAlerts", Number(event.target.value))
                      }
                      className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
                    />
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-col gap-2 lg:flex-row lg:items-center lg:justify-between">
              <div>
                <CardTitle>{t("incidentPolicy.composer.ruleBuilder.title")}</CardTitle>
                <p className="text-sm text-gray-500">
                  {t("incidentPolicy.composer.ruleBuilder.description")}
                </p>
              </div>
              <div className="flex gap-2">
                <Button variant="ghost" size="sm" disabled className="gap-2">
                  <Layers3 className="h-4 w-4" />
                  {t("incidentPolicy.composer.ruleBuilder.nested")}
                </Button>
                <Button variant="secondary" size="sm" className="gap-2" onClick={handleAddCondition}>
                  <Plus className="h-4 w-4" />
                  {t("incidentPolicy.ruleEditor.addCondition")}
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between rounded-lg border border-gray-200 bg-gray-50 px-4 py-3">
                <div className="flex items-center gap-2 text-sm font-semibold text-gray-700">
                  {t("incidentPolicy.composer.ruleBuilder.groupLabel")}
                </div>
                <div className="flex items-center gap-2">
                  {["AND", "OR"].map((logic) => (
                    <button
                      key={logic}
                      type="button"
                      onClick={() => handleLogicChange(logic as "AND" | "OR")}
                      className={cn(
                        "rounded-md px-3 py-1.5 text-sm font-semibold transition-colors",
                        policy.rule.logic === logic
                          ? "bg-blue-600 text-white"
                          : "text-gray-500 hover:bg-gray-100",
                      )}
                    >
                      {logic}
                    </button>
                  ))}
                </div>
              </div>

              {policy.rule.conditions.map((condition, index) => (
                <div key={condition.id} className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
                  <div className="mb-3 flex items-center justify-between text-sm font-medium text-gray-600">
                    <span>
                      {t("incidentPolicy.composer.ruleBuilder.conditionLabel", { index: index + 1 })}
                    </span>
                    <button
                      type="button"
                      className="text-red-500 transition-colors hover:text-red-600"
                      onClick={() => handleRemoveCondition(condition.id)}
                    >
                      <Trash2 className="mr-1 inline-block h-4 w-4" />
                      {t("incidentPolicy.ruleEditor.remove")}
                    </button>
                  </div>

                  <div className="grid gap-3 xl:grid-cols-7">
                    <div className="xl:col-span-2">
                      <label className="text-xs font-semibold uppercase tracking-wide text-gray-500">
                        {t("incidentPolicy.ruleEditor.metric")}
                      </label>
                      <select
                        value={condition.metric}
                        onChange={(event) =>
                          handleConditionChange(condition.id, "metric", event.target.value)
                        }
                        className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
                      >
                        {METRIC_OPTIONS.map((metric) => (
                          <option key={metric} value={metric}>
                            {metric}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="text-xs font-semibold uppercase tracking-wide text-gray-500">
                        {t("incidentPolicy.composer.ruleBuilder.compareTarget")}
                      </label>
                      <select
                        value={condition.compareTarget}
                        onChange={(event) =>
                          handleConditionChange(condition.id, "compareTarget", event.target.value)
                        }
                        className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
                      >
                        {COMPARE_TARGET_OPTIONS.map((option) => (
                          <option key={option.value} value={option.value}>
                            {option.label}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="text-xs font-semibold uppercase tracking-wide text-gray-500">
                        {t("incidentPolicy.ruleEditor.operator")}
                      </label>
                      <select
                        value={condition.operator}
                        onChange={(event) =>
                          handleConditionChange(condition.id, "operator", event.target.value)
                        }
                        className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
                      >
                        {OPERATOR_OPTIONS.map((option) => (
                          <option key={option.value} value={option.value}>
                            {option.label}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="text-xs font-semibold uppercase tracking-wide text-gray-500">
                        {t("incidentPolicy.composer.ruleBuilder.deviation")}
                      </label>
                      <input
                        type="number"
                        value={condition.deviation}
                        onChange={(event) =>
                          handleConditionChange(condition.id, "deviation", Number(event.target.value))
                        }
                        className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
                      />
                    </div>
                    <div>
                      <label className="text-xs font-semibold uppercase tracking-wide text-gray-500">
                        {t("incidentPolicy.composer.ruleBuilder.baseline")}
                      </label>
                      <select
                        value={condition.baseline}
                        onChange={(event) =>
                          handleConditionChange(condition.id, "baseline", event.target.value)
                        }
                        className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
                      >
                        {BASELINE_OPTIONS.map((option) => (
                          <option key={option} value={option}>
                            {option}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="text-xs font-semibold uppercase tracking-wide text-gray-500">
                        {t("incidentPolicy.composer.ruleBuilder.window")}
                      </label>
                      <select
                        value={condition.window}
                        onChange={(event) =>
                          handleConditionChange(condition.id, "window", event.target.value)
                        }
                        className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
                      >
                        {WINDOW_OPTIONS.map((option) => (
                          <option key={option} value={option}>
                            {option}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="text-xs font-semibold uppercase tracking-wide text-gray-500">
                        {t("incidentPolicy.composer.ruleBuilder.stat")}
                      </label>
                      <select
                        value={condition.stat}
                        onChange={(event) =>
                          handleConditionChange(condition.id, "stat", event.target.value)
                        }
                        className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
                      >
                        {STAT_OPTIONS.map((option) => (
                          <option key={option} value={option}>
                            {option}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>{t("incidentPolicy.composer.response.title")}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-4 md:grid-cols-3">
                <TogglePill
                  label={t("incidentPolicy.composer.response.slack")}
                  active={policy.response.slackAlert}
                  onClick={() => handleResponseToggle("slackAlert")}
                />
                <TogglePill
                  label={t("incidentPolicy.composer.response.enforce")}
                  active={policy.response.enforce}
                  variant="danger"
                  onClick={() => handleResponseToggle("enforce")}
                />
                <TogglePill
                  label={t("incidentPolicy.composer.response.waiver")}
                  active={policy.response.waiver}
                  variant="success"
                  onClick={() => handleResponseToggle("waiver")}
                />
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <div className="flex flex-col gap-2">
                  <label className="text-sm font-medium text-gray-700">
                    {t("incidentPolicy.composer.response.tags")}
                  </label>
                  <input
                    type="text"
                    value={policy.response.tags.join(", ")}
                    onChange={(event) => handleResponseTagsChange(event.target.value)}
                    className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
                    placeholder="tag-a, tag-b"
                  />
                </div>
                <div className="flex flex-col gap-2">
                  <label className="text-sm font-medium text-gray-700">
                    {t("incidentPolicy.composer.response.severity")}
                  </label>
                  <select
                    value={policy.response.severity}
                    onChange={(event) =>
                      handleResponseSeverityChange(
                        event.target.value as IncidentPolicyDetail["response"]["severity"],
                      )
                    }
                    className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
                  >
                    <option value="warn">{t("incidentPolicy.composer.response.severityWarn")}</option>
                    <option value="block">{t("incidentPolicy.composer.response.severityBlock")}</option>
                    <option value="info">{t("incidentPolicy.composer.response.severityInfo")}</option>
                  </select>
                </div>
              </div>

              <div className="flex flex-col gap-2">
                <label className="text-sm font-medium text-gray-700">
                  {t("incidentPolicy.composer.response.memo")}
                </label>
                <textarea
                  value={policy.response.memo}
                  onChange={(event) => handleResponseMemoChange(event.target.value)}
                  rows={3}
                  className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
                  placeholder={t("incidentPolicy.composer.response.memoPlaceholder") ?? ""}
                />
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader className="flex items-center justify-between">
              <CardTitle>{t("incidentPolicy.composer.preview.title")}</CardTitle>
              <Badge variant="info">{policy.status.toUpperCase()}</Badge>
            </CardHeader>
            <CardContent className="space-y-4 text-sm text-gray-700">
              <div>
                <h3 className="text-xs font-semibold uppercase tracking-wide text-gray-500">
                  {t("incidentPolicy.composer.preview.scope")}
                </h3>
                <p className="mt-1">
                  env: <span className="font-medium">{policy.scope.environment}</span> · selector: {policy.scope.selector}
                </p>
                <p className="text-xs text-gray-500">
                  {t("incidentPolicy.composer.preview.scheduleSummary", {
                    mode: policy.schedule.mode,
                    interval: policy.schedule.interval,
                    timezone: policy.schedule.timezone,
                  })}
                </p>
              </div>
              <div>
                <h3 className="text-xs font-semibold uppercase tracking-wide text-gray-500">
                  {t("incidentPolicy.composer.preview.rule")}
                </h3>
                <p className="mt-1 whitespace-pre-line font-mono text-xs text-blue-700">
                  {rulePreview}
                </p>
              </div>
              <div>
                <h3 className="text-xs font-semibold uppercase tracking-wide text-gray-500">
                  {t("incidentPolicy.composer.preview.response")}
                </h3>
                <p className="mt-1">
                  {policy.response.slackAlert
                    ? t("incidentPolicy.composer.preview.slackOn")
                    : t("incidentPolicy.composer.preview.slackOff")}
                </p>
                <p className="text-xs text-gray-500">
                  {t("incidentPolicy.composer.preview.tags", {
                    tags: policy.response.tags.join(", "),
                  })}
                </p>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex items-center justify-between">
              <CardTitle>{t("incidentPolicy.composer.preview.jsonTitle")}</CardTitle>
              <Button variant="ghost" size="sm" className="gap-2" onClick={handleCopyJson}>
                <Copy className="h-4 w-4" />
                {t("incidentPolicy.composer.preview.copyJson")}
              </Button>
            </CardHeader>
            <CardContent>
              <pre className="max-h-[320px] overflow-auto rounded-lg bg-gray-900 p-4 text-xs text-gray-100">
{jsonPreview}
              </pre>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>{t("incidentPolicy.composer.meta.title")}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm text-gray-600">
              <p>
                <span className="font-semibold text-gray-800">{t("incidentPolicy.composer.meta.id")}</span>
                : {policy.id}
              </p>
              <p>
                <span className="font-semibold text-gray-800">{t("incidentPolicy.composer.meta.owner")}</span>
                : @{policy.createdBy}
              </p>
              <p>
                <span className="font-semibold text-gray-800">{t("incidentPolicy.composer.meta.createdAt")}</span>
                : {policy.createdAt}
              </p>
              <p>
                <span className="font-semibold text-gray-800">{t("incidentPolicy.composer.meta.valid")}</span>
                : {policy.validPeriod}
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

interface TogglePillProps {
  label: string;
  active: boolean;
  onClick: () => void;
  variant?: "default" | "success" | "danger";
}

function TogglePill({ label, active, onClick, variant = "default" }: TogglePillProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "flex items-center justify-between rounded-lg border px-3 py-2 text-sm font-medium transition-colors",
        active ? "border-blue-500 bg-blue-50 text-blue-600" : "border-gray-200 bg-white text-gray-500 hover:border-gray-300",
        variant === "success" && active ? "border-green-500 bg-green-50 text-green-600" : undefined,
        variant === "danger" && active ? "border-red-500 bg-red-50 text-red-600" : undefined,
      )}
    >
      <span>{label}</span>
      <span
        className={cn(
          "inline-flex h-5 w-10 items-center rounded-full border px-1 transition-colors",
          active ? "border-current bg-current/20" : "border-gray-300 bg-gray-200",
        )}
      >
        <span
          className={cn(
            "h-3.5 w-3.5 rounded-full bg-white shadow transition-transform",
            active ? "translate-x-4" : "translate-x-0",
          )}
        />
      </span>
    </button>
  );
}
