import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/Card";
import Button from "../components/ui/Button";
import Badge from "../components/ui/Badge";
import Loading from "../components/ui/Loading";
import { schemasAPI } from "../services/api";
import { RefreshCw, FileCode, Shield } from "lucide-react";

interface SchemaArtifact {
  subject: string;
  version: number;
  storage_url: string;
  checksum: string;
  schema_type: string;
  compatibility_mode: string | null;
  owner: string | null;
}

export default function Analysis() {
  const { t } = useTranslation();
  const [schemas, setSchemas] = useState<SchemaArtifact[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");

  useEffect(() => {
    loadSchemas();
  }, []);

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

  // 검색 필터링
  const filteredSchemas = schemas.filter(schema =>
    schema.subject.toLowerCase().includes(searchTerm.toLowerCase()) ||
    schema.owner?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  // 통계 계산
  const subjectCount = new Set(schemas.map(s => s.subject)).size;
  const ownerCount = new Set(schemas.map(s => s.owner).filter(Boolean)).size;
  const compatibilityModes = schemas.reduce((acc, s) => {
    const mode = s.compatibility_mode || "NONE";
    acc[mode] = (acc[mode] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  const getCompatibilityBadgeVariant = (mode: string | null) => {
    if (!mode || mode === "NONE") return "default";
    if (mode === "BACKWARD" || mode === "BACKWARD_TRANSITIVE") return "success";
    if (mode === "FORWARD" || mode === "FORWARD_TRANSITIVE") return "info";
    if (mode === "FULL" || mode === "FULL_TRANSITIVE") return "warning";
    return "default";
  };

  const getSchemaTypeBadgeVariant = (type: string) => {
    switch (type.toUpperCase()) {
      case "AVRO": return "info";
      case "PROTOBUF": return "success";
      case "JSON": return "warning";
      default: return "default";
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
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">{t("analysis.title")}</h1>
          <p className="mt-2 text-gray-600">
            {t("analysis.description")}
          </p>
        </div>
        <Button variant="secondary" onClick={loadSchemas} disabled={loading}>
          <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          {t("common.filter")}
        </Button>
      </div>

      {/* Statistics Cards */}
      <div className="grid gap-6 md:grid-cols-3">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">{t("analysis.totalSchemas")}</p>
                <p className="text-3xl font-bold text-gray-900 mt-2">{subjectCount}</p>
                <p className="text-sm text-gray-500 mt-1">Unique Subjects</p>
              </div>
              <div className="h-12 w-12 rounded-full bg-blue-100 flex items-center justify-center">
                <FileCode className="h-6 w-6 text-blue-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">{t("analysis.owner")}</p>
                <p className="text-3xl font-bold text-gray-900 mt-2">{ownerCount}</p>
                <p className="text-sm text-gray-500 mt-1">Unique Teams</p>
              </div>
              <div className="h-12 w-12 rounded-full bg-green-100 flex items-center justify-center">
                <Shield className="h-6 w-6 text-green-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div>
              <p className="text-sm font-medium text-gray-600">{t("analysis.compatibilityMode")}</p>
              <div className="mt-2 space-y-1">
                {Object.entries(compatibilityModes).map(([mode, count]) => (
                  <div key={mode} className="flex items-center justify-between text-sm">
                    <span className="text-gray-700">{mode}</span>
                    <span className="font-semibold text-gray-900">{count}</span>
                  </div>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Search */}
      <Card className="p-4">
        <input
          type="text"
          placeholder="Search by subject or owner..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="w-full rounded-lg border border-gray-300 px-4 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
      </Card>

      {/* Schemas Table */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileCode className="h-5 w-5" />
            {t("analysis.schemaUsageReport")} ({filteredSchemas.length})
          </CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex h-64 items-center justify-center">
              <Loading size="lg" />
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-200">
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">
                      {t("analysis.subject")}
                    </th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">
                      {t("analysis.version")}
                    </th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">
                      {t("analysis.schemaType")}
                    </th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">
                      {t("analysis.compatibilityMode")}
                    </th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">
                      {t("analysis.owner")}
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {filteredSchemas.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="px-4 py-8 text-center text-gray-500">
                        {t("analysis.noSchemas")}
                      </td>
                    </tr>
                  ) : (
                    filteredSchemas.map((schema, index) => (
                      <tr key={`${schema.subject}-${index}`} className="hover:bg-gray-50">
                        <td className="px-4 py-3 text-sm font-medium text-gray-900">
                          {schema.subject}
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-600">
                          v{schema.version}
                        </td>
                        <td className="px-4 py-3">
                          <Badge variant={getSchemaTypeBadgeVariant(schema.schema_type)}>
                            {schema.schema_type}
                          </Badge>
                        </td>
                        <td className="px-4 py-3">
                          <Badge variant={getCompatibilityBadgeVariant(schema.compatibility_mode)}>
                            {schema.compatibility_mode || "NONE"}
                          </Badge>
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-600">
                          {schema.owner || "-"}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
