import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/Card";
import Button from "../components/ui/Button";
import Badge from "../components/ui/Badge";
import Loading from "../components/ui/Loading";
import UploadSchemaModal from "../components/schema/UploadSchemaModal";
import { schemasAPI, clustersAPI } from "../services/api";
import { Upload, RefreshCw, Trash2, Search } from "lucide-react";
import type { SchemaArtifact } from "../types";

export default function Schemas() {
  const [schemas, setSchemas] = useState<SchemaArtifact[]>([]);
  const [selectedRegistry, setSelectedRegistry] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [showUploadModal, setShowUploadModal] = useState(false);

  const loadRegistries = async () => {
    try {
      const response = await clustersAPI.listRegistries();
      if (response.data.length > 0) {
        setSelectedRegistry(response.data[0].registry_id);
      }
    } catch (error) {
      console.error("Failed to load registries:", error);
    }
  };

  const loadSchemas = async () => {
    try {
      setLoading(true);
      const response = await schemasAPI.list();
      setSchemas(response.data);
    } catch (error) {
      console.error("Failed to load schemas:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRegistries();
  }, []);

  useEffect(() => {
    if (selectedRegistry) {
      loadSchemas();
    }
  }, [selectedRegistry]);

  const handleUploadSchema = async (registryId: string, formData: FormData) => {
    try {
      await schemasAPI.upload(registryId, formData);
      await loadSchemas();
    } catch (error) {
      console.error("Failed to upload schema:", error);
      throw error;
    }
  };

  const filteredSchemas = schemas.filter((schema) =>
    schema.subject.toLowerCase().includes(searchQuery.toLowerCase())
  );

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
          <h1 className="text-3xl font-bold text-gray-900">Schemas</h1>
          <p className="mt-2 text-gray-600">스키마를 관리합니다</p>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={loadSchemas}>
            <RefreshCw className="h-4 w-4" />
            Refresh
          </Button>
          <Button onClick={() => setShowUploadModal(true)}>
            <Upload className="h-4 w-4" />
            Upload Schema
          </Button>
        </div>
      </div>

      {/* Upload Schema Modal */}
      <UploadSchemaModal
        isOpen={showUploadModal}
        onClose={() => setShowUploadModal(false)}
        onSubmit={handleUploadSchema}
        registryId={selectedRegistry}
      />

      {/* Search */}
      <Card>
        <CardContent className="pt-6">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search schemas..."
              className="w-full rounded-lg border border-gray-300 pl-10 pr-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
        </CardContent>
      </Card>

      {/* Schemas Table */}
      <Card>
        <CardHeader>
          <CardTitle>Schemas ({filteredSchemas.length})</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">
                    Subject
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">
                    Version
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">
                    Type
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">
                    Compatibility
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">
                    Owner
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {filteredSchemas.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-4 py-8 text-center text-gray-500">
                      No schemas found
                    </td>
                  </tr>
                ) : (
                  filteredSchemas.map((schema) => (
                    <tr key={schema.subject + schema.version} className="hover:bg-gray-50">
                      <td className="px-4 py-3 text-sm font-medium text-gray-900">
                        {schema.subject}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600">
                        v{schema.version}
                      </td>
                      <td className="px-4 py-3">
                        <Badge variant="info">{schema.schema_type}</Badge>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600">
                        {schema.compatibility_mode || "-"}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600">
                        {schema.owner || "-"}
                      </td>
                      <td className="px-4 py-3">
                        <Button size="sm" variant="ghost">
                          <Trash2 className="h-4 w-4 text-red-600" />
                        </Button>
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
