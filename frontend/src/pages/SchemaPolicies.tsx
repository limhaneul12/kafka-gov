import { useState } from "react";
import { toast } from "sonner";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/Card";
import Button from "../components/ui/Button";
import Badge from "../components/ui/Badge";
import { Plus, RefreshCw, Shield, FileCode } from "lucide-react";

export default function SchemaPolicies() {
  const [loading, setLoading] = useState(false);

  const handleRefresh = () => {
    setLoading(true);
    setTimeout(() => {
      setLoading(false);
      toast.success("Schema policies refreshed");
    }, 500);
  };

  const handleCreateNew = () => {
    toast.info("Schema policy creation coming soon");
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Schema Policies</h1>
          <p className="mt-1 text-sm text-gray-500">
            Manage subject naming strategies and validation rules for schemas
          </p>
        </div>
        <div className="flex gap-2">
          <Button onClick={handleRefresh} variant="secondary" disabled={loading}>
            <RefreshCw className={`h-4 w-4 mr-2 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </Button>
          <Button onClick={handleCreateNew}>
            <Plus className="h-4 w-4 mr-2" />
            Create Policy
          </Button>
        </div>
      </div>

      {/* Naming Strategy Info */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5" />
            Subject Naming Strategies
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div>
              <h4 className="font-medium text-sm text-gray-700 mb-2">SR Built-in Strategies</h4>
              <div className="grid gap-2 md:grid-cols-3">
                <div className="p-3 border rounded-lg">
                  <Badge className="mb-2">TopicNameStrategy</Badge>
                  <p className="text-xs text-gray-600">Format: topic-key/value</p>
                </div>
                <div className="p-3 border rounded-lg">
                  <Badge className="mb-2">RecordNameStrategy</Badge>
                  <p className="text-xs text-gray-600">Format: namespace.record</p>
                </div>
                <div className="p-3 border rounded-lg">
                  <Badge className="mb-2">TopicRecordNameStrategy</Badge>
                  <p className="text-xs text-gray-600">Format: topic-namespace.record</p>
                </div>
              </div>
            </div>

            <div>
              <h4 className="font-medium text-sm text-gray-700 mb-2">Kafka-Gov Extended Strategies</h4>
              <div className="grid gap-2 md:grid-cols-3">
                <div className="p-3 border rounded-lg bg-blue-50">
                  <Badge variant="success" className="mb-2">EnvPrefixed</Badge>
                  <p className="text-xs text-gray-600">Format: env.topic-namespace.record</p>
                </div>
                <div className="p-3 border rounded-lg bg-blue-50">
                  <Badge variant="success" className="mb-2">TeamScoped</Badge>
                  <p className="text-xs text-gray-600">Format: team.namespace.record</p>
                </div>
                <div className="p-3 border rounded-lg bg-blue-50">
                  <Badge variant="success" className="mb-2">CompactRecord</Badge>
                  <p className="text-xs text-gray-600">Format: record only</p>
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Empty State */}
      <Card>
        <CardContent className="text-center py-12">
          <FileCode className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">Schema Policy Management</h3>
          <p className="text-sm text-gray-500 mb-4 max-w-md mx-auto">
            Schema policies are currently managed through the upload process. 
            Select a naming strategy when uploading schemas to ensure consistent subject naming.
          </p>
          <div className="flex gap-2 justify-center">
            <Button variant="secondary" onClick={() => window.location.href = "/schemas"}>
              Go to Schemas
            </Button>
            <Button onClick={handleCreateNew}>
              <Plus className="h-4 w-4 mr-2" />
              Create Custom Policy
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Documentation */}
      <Card>
        <CardHeader>
          <CardTitle>Naming Strategy Guidelines</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3 text-sm text-gray-700">
            <div>
              <strong>Security Validation:</strong>
              <ul className="list-disc list-inside ml-2 text-gray-600">
                <li>Only alphanumeric characters, dots, hyphens, and underscores allowed</li>
                <li>Maximum length: 200 characters</li>
                <li>No forbidden prefixes in production environment</li>
              </ul>
            </div>
            <div>
              <strong>Best Practices:</strong>
              <ul className="list-disc list-inside ml-2 text-gray-600">
                <li>Use environment-prefixed strategies for multi-environment setups</li>
                <li>Maintain consistent naming across your organization</li>
                <li>Document your chosen strategy in team guidelines</li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
