import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/Card";
import Button from "../components/ui/Button";
import Loading from "../components/ui/Loading";
import { analysisAPI } from "../services/api";
import { RefreshCw, Activity, Link as LinkIcon } from "lucide-react";
import type { TopicSchemaCorrelation } from "../types";

export default function Analysis() {
  const [correlations, setCorrelations] = useState<TopicSchemaCorrelation[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadCorrelations();
  }, []);

  const loadCorrelations = async () => {
    try {
      setLoading(true);
      const response = await analysisAPI.correlations();
      setCorrelations(response.data);
    } catch (error) {
      console.error("Failed to load correlations:", error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex h-96 items-center justify-center">
        <Loading size="lg" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Analysis</h1>
          <p className="mt-2 text-gray-600">
            토픽과 스키마의 상관관계를 분석합니다
          </p>
        </div>
        <Button variant="secondary" onClick={loadCorrelations}>
          <RefreshCw className="h-4 w-4" />
          Refresh
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Activity className="h-5 w-5" />
            Topic-Schema Correlations ({correlations.length})
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">
                    Topic
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">
                    Key Schema
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">
                    Value Schema
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">
                    Environment
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">
                    Source
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">
                    Confidence
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {correlations.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-4 py-8 text-center text-gray-500">
                      No correlations found
                    </td>
                  </tr>
                ) : (
                  correlations.map((correlation) => (
                    <tr key={correlation.correlation_id} className="hover:bg-gray-50">
                      <td className="px-4 py-3 text-sm font-medium text-gray-900">
                        {correlation.topic_name}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600">
                        {correlation.key_schema_subject || "-"}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600">
                        {correlation.value_schema_subject || "-"}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600">
                        {correlation.environment}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-1 text-sm text-gray-600">
                          <LinkIcon className="h-3 w-3" />
                          {correlation.link_source}
                        </div>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600">
                        {(correlation.confidence_score * 100).toFixed(0)}%
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
