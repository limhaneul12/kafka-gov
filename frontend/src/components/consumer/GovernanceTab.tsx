import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Card, CardContent, CardHeader, CardTitle } from "../ui/Card";
import Badge from "../ui/Badge";
import Loading from "../ui/Loading";
import { consumerAPI } from "../../services/api";
import type { ConsumerGroupMetrics, PolicyAdvice } from "../../types";

interface GovernanceTabProps {
  metrics: ConsumerGroupMetrics;
  groupId: string;
  clusterId: string;
}

export default function GovernanceTab({
  metrics,
  groupId,
  clusterId,
}: GovernanceTabProps) {
  const [advice, setAdvice] = useState<PolicyAdvice | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadAdvice();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [groupId, clusterId]);

  const loadAdvice = async () => {
    try {
      setLoading(true);
      const response = await consumerAPI.getAdvice(clusterId, groupId);
      setAdvice(response.data);
    } catch (error) {
      console.error("Failed to load policy advice:", error);
      toast.error("Failed to load policy advice");
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex h-48 items-center justify-center">
        <Loading />
      </div>
    );
  }

  const sloColor = (rate: number) => {
    if (rate >= 0.95) return "emerald";
    if (rate >= 0.8) return "yellow";
    return "rose";
  };

  return (
    <div className="space-y-6">
      {/* SLO Compliance */}
      <Card>
        <CardHeader>
          <CardTitle>SLO Compliance</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Compliance Rate</p>
                <div className="mt-2 flex items-baseline gap-2">
                  <p className="text-3xl font-bold text-gray-900">
                    {(metrics.advice.slo_compliance_rate * 100).toFixed(1)}%
                  </p>
                  <Badge color={sloColor(metrics.advice.slo_compliance_rate)}>
                    {metrics.advice.slo_compliance_rate >= 0.95
                      ? "Excellent"
                      : metrics.advice.slo_compliance_rate >= 0.8
                      ? "Good"
                      : "Needs Attention"}
                  </Badge>
                </div>
              </div>
              <div className="w-32 h-32">
                <svg viewBox="0 0 100 100" className="w-full h-full -rotate-90">
                  <circle
                    cx="50"
                    cy="50"
                    r="40"
                    fill="none"
                    stroke="#e5e7eb"
                    strokeWidth="12"
                  />
                  <circle
                    cx="50"
                    cy="50"
                    r="40"
                    fill="none"
                    stroke={
                      metrics.advice.slo_compliance_rate >= 0.95
                        ? "#10b981"
                        : metrics.advice.slo_compliance_rate >= 0.8
                        ? "#eab308"
                        : "#f43f5e"
                    }
                    strokeWidth="12"
                    strokeDasharray={`${
                      metrics.advice.slo_compliance_rate * 251.2
                    } 251.2`}
                    strokeLinecap="round"
                  />
                </svg>
              </div>
            </div>

            {metrics.advice.risk_eta && (
              <div className="mt-4 p-4 bg-rose-50 rounded-lg border border-rose-200">
                <p className="text-sm font-medium text-rose-900">
                  ⚠️ Delivery Risk Warning
                </p>
                <p className="text-sm text-rose-700 mt-1">
                  Estimated SLO violation ETA:{" "}
                  {new Date(metrics.advice.risk_eta).toLocaleString()}
                </p>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Policy Advice */}
      {advice && (
        <>
          {/* Assignor Recommendation */}
          {advice.assignor.recommendation && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  Partition Assignor
                  <Badge color="blue">Recommendation</Badge>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="p-4 bg-blue-50 rounded-lg">
                    <p className="font-medium text-blue-900">
                      {advice.assignor.recommendation}
                    </p>
                  </div>
                  {advice.assignor.reason && (
                    <p className="text-sm text-gray-600">
                      <strong>Reason:</strong> {advice.assignor.reason}
                    </p>
                  )}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Static Membership */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                Static Membership
                {advice.static_membership.recommended && (
                  <Badge color="yellow">Recommended</Badge>
                )}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <div
                  className={`p-4 rounded-lg ${
                    advice.static_membership.recommended
                      ? "bg-yellow-50"
                      : "bg-emerald-50"
                  }`}
                >
                  <p
                    className={`font-medium ${
                      advice.static_membership.recommended
                        ? "text-yellow-900"
                        : "text-emerald-900"
                    }`}
                  >
                    {advice.static_membership.recommended
                      ? "Enable static membership (group.instance.id)"
                      : "Current configuration is optimal"}
                  </p>
                </div>
                {advice.static_membership.reason && (
                  <p className="text-sm text-gray-600">
                    <strong>Reason:</strong> {advice.static_membership.reason}
                  </p>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Scale Recommendation */}
          {advice.scale.recommendation && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  Scaling Recommendation
                  <Badge color="rose">Action Required</Badge>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="p-4 bg-rose-50 rounded-lg border border-rose-200">
                    <p className="font-medium text-rose-900">
                      {advice.scale.recommendation === "increase_consumers"
                        ? "Increase consumer instances"
                        : "Add more partitions to topics"}
                    </p>
                  </div>
                  {advice.scale.reason && (
                    <p className="text-sm text-gray-600">
                      <strong>Reason:</strong> {advice.scale.reason}
                    </p>
                  )}
                </div>
              </CardContent>
            </Card>
          )}
        </>
      )}

      {/* Summary */}
      <Card>
        <CardHeader>
          <CardTitle>Governance Summary</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between py-2 border-b">
              <span className="text-gray-600">SLO Compliance</span>
              <span className="font-medium">
                {(metrics.advice.slo_compliance_rate * 100).toFixed(1)}%
              </span>
            </div>
            <div className="flex justify-between py-2 border-b">
              <span className="text-gray-600">Assignor Status</span>
              <span className="font-medium">
                {metrics.advice.assignor_recommendation || "Optimal"}
              </span>
            </div>
            <div className="flex justify-between py-2 border-b">
              <span className="text-gray-600">Static Membership</span>
              <span className="font-medium">
                {metrics.advice.static_membership_recommended
                  ? "Recommended"
                  : "Not Needed"}
              </span>
            </div>
            <div className="flex justify-between py-2">
              <span className="text-gray-600">Scaling Required</span>
              <span className="font-medium">
                {metrics.advice.scale_recommendation || "No"}
              </span>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
