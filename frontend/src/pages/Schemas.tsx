import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/Card";
import Button from "../components/ui/Button";
import Badge from "../components/ui/Badge";
import Loading from "../components/ui/Loading";
import UploadSchemaModal from "../components/schema/UploadSchemaModal";
import { schemasAPI, clustersAPI } from "../services/api";
import { Upload, RefreshCw, Trash2, Search, Database } from "lucide-react";
import { toast } from "sonner";
import type { SchemaArtifact } from "../types";

export default function Schemas() {
  const { t } = useTranslation();
  const [schemas, setSchemas] = useState<SchemaArtifact[]>([]);
  const [registries, setRegistries] = useState<Array<{ registry_id: string; name?: string }>>([]);
  const [selectedRegistry, setSelectedRegistry] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [showUploadModal, setShowUploadModal] = useState(false);

  const loadRegistries = async () => {
    try {
      const response = await clustersAPI.listRegistries();
      setRegistries(response.data);
      if (response.data.length > 0) {
        setSelectedRegistry(response.data[0].registry_id);
      }
    } catch (error) {
      console.error("Failed to load registries:", error);
    } finally {
      setLoading(false);
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

  const handleRefresh = async () => {
    if (!selectedRegistry) {
      toast.error('Registry Selection Required', {
        description: 'Please select a Schema Registry to sync'
      });
      return;
    }

    try {
      setLoading(true);
      toast.info('Sync Started', {
        description: 'Fetching schemas from Schema Registry...'
      });
      
      // Schema Registry와 동기화
      const syncResult = await schemasAPI.sync(selectedRegistry);
      
      // 동기화 후 목록 다시 로드
      await loadSchemas();
      
      toast.success('Sync Completed', {
        description: `${syncResult.data.synced_count || syncResult.data.total || 0} schemas synchronized`
      });
    } catch (error: unknown) {
      console.error("Failed to sync schemas:", error);
      
      // Axios 에러에서 상세 메시지 추출
      let errorMessage = 'Schema synchronization failed';
      if (error && typeof error === 'object' && 'response' in error) {
        const axiosError = error as { response?: { data?: { detail?: string }; status?: number } };
        console.error('Sync error details:', axiosError.response);
        
        if (axiosError.response?.data?.detail) {
          errorMessage = axiosError.response.data.detail;
        } else if (axiosError.response?.status === 405) {
          errorMessage = `Method Not Allowed - Check API endpoint configuration`;
        } else if (axiosError.response?.status === 422) {
          errorMessage = `Schema Registry not found. Please check "${selectedRegistry}" connection in Settings`;
        } else if (axiosError.response?.status) {
          errorMessage = `HTTP ${axiosError.response.status}: ${JSON.stringify(axiosError.response.data)}`;
        }
      } else if (error instanceof Error) {
        errorMessage = error.message;
      }
      
      toast.error('Sync Failed', {
        description: errorMessage,
        duration: 7000,
      });
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

  const handleDeleteSchema = async (subject: string) => {
    if (!selectedRegistry) {
      toast.error('Registry Selection Required', {
        description: 'Please select a Schema Registry'
      });
      return;
    }

    if (!confirm(`Are you sure you want to delete schema "${subject}"?`)) {
      return;
    }

    try {
      setLoading(true);
      await schemasAPI.delete(selectedRegistry, subject);
      await loadSchemas();
      toast.success('Schema Deleted', {
        description: `Schema "${subject}" has been deleted successfully`
      });
    } catch (error: unknown) {
      console.error("Failed to delete schema:", error);
      
      let errorMessage = 'Failed to delete schema';
      if (error && typeof error === 'object' && 'response' in error) {
        const axiosError = error as { response?: { data?: { detail?: string } } };
        if (axiosError.response?.data?.detail) {
          errorMessage = axiosError.response.data.detail;
        }
      } else if (error instanceof Error) {
        errorMessage = error.message;
      }
      
      toast.error('Delete Failed', {
        description: errorMessage,
        duration: 5000,
      });
    } finally {
      setLoading(false);
    }
  };

  const filteredSchemas = schemas.filter((schema) =>
    schema.subject.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // Registry 연결 없음
  if (!loading && registries.length === 0) {
    return (
      <div className="flex h-96 items-center justify-center">
        <div className="text-center">
          <Database className="h-16 w-16 text-gray-400 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-gray-900 mb-2">
            {t("schema.notConfigured")}
          </h2>
          <p className="text-gray-600">
            {t("schema.pleaseConfigureFirst")}
          </p>
        </div>
      </div>
    );
  }

  if (loading && !schemas.length) {
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
          <h1 className="text-3xl font-bold text-gray-900">{t("schema.list")}</h1>
          <p className="mt-2 text-gray-600">{t("schema.description")}</p>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={handleRefresh}>
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

      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Schema Registry
              </label>
              <select
                value={selectedRegistry}
                onChange={(e) => setSelectedRegistry(e.target.value)}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                {registries.length === 0 ? (
                  <option value="">No registries available</option>
                ) : (
                  registries.map((registry) => (
                    <option key={registry.registry_id} value={registry.registry_id}>
                      {registry.name || registry.registry_id}
                    </option>
                  ))
                )}
              </select>
              {registries.length === 0 && (
                <p className="mt-1 text-xs text-orange-600">
                  ⚠️ Settings에서 Schema Registry를 먼저 등록하세요.
                </p>
              )}
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Search
              </label>
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
            </div>
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
                        <Button 
                          size="sm" 
                          variant="ghost"
                          onClick={() => handleDeleteSchema(schema.subject)}
                        >
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
