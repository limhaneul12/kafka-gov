import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/Card";
import Button from "../components/ui/Button";
import Badge from "../components/ui/Badge";
import Loading from "../components/ui/Loading";
import { policiesAPI } from "../services/api";
import { Plus, RefreshCw, Shield } from "lucide-react";
import type { Policy } from "../types";

export default function Policies() {
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadPolicies();
  }, []);

  const loadPolicies = async () => {
    try {
      setLoading(true);
      const response = await policiesAPI.list();
      setPolicies(response.data.policies || []);
    } catch (error) {
      console.error("Failed to load policies:", error);
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadgeVariant = (status: string) => {
    switch (status) {
      case "ACTIVE":
        return "success";
      case "DRAFT":
        return "warning";
      case "ARCHIVED":
        return "default";
      default:
        return "default";
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
          <h1 className="text-3xl font-bold text-gray-900">Policies</h1>
          <p className="mt-2 text-gray-600">정책을 관리합니다</p>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={loadPolicies}>
            <RefreshCw className="h-4 w-4" />
            Refresh
          </Button>
          <Button>
            <Plus className="h-4 w-4" />
            Create Policy
          </Button>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5" />
            Policies ({policies.length})
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">
                    Name
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">
                    Type
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">
                    Version
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">
                    Status
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">
                    Created By
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">
                    Updated
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {policies.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-4 py-8 text-center text-gray-500">
                      No policies found
                    </td>
                  </tr>
                ) : (
                  policies.map((policy) => (
                    <tr key={policy.policy_id} className="hover:bg-gray-50">
                      <td className="px-4 py-3 text-sm font-medium text-gray-900">
                        {policy.name}
                      </td>
                      <td className="px-4 py-3">
                        <Badge variant="info">{policy.policy_type}</Badge>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600">
                        v{policy.version}
                      </td>
                      <td className="px-4 py-3">
                        <Badge variant={getStatusBadgeVariant(policy.status)}>
                          {policy.status}
                        </Badge>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600">
                        {policy.created_by}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600">
                        {new Date(policy.updated_at).toLocaleDateString()}
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
