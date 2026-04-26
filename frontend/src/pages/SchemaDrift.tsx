import { useCallback, useEffect, useMemo, useState } from "react";
import { AlertTriangle, RefreshCw, Radar } from "lucide-react";
import { toast } from "sonner";

import Badge from "../components/ui/Badge";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/Card";
import Button from "../components/ui/Button";
import Loading from "../components/ui/Loading";
import schemaApi from "../services/schemaApi";
import type { SchemaArtifactResponse, SchemaDriftResponse } from "../types/schema";
import { extractErrorMessage } from "../utils/error";
import { resolveActiveRegistry } from "../utils/schemaGovernance";

type DriftRow = {
  subject: string;
  owner: string | null;
  compatibility_mode: string | null;
  version: number | null;
  drift: SchemaDriftResponse | null;
};

export default function SchemaDrift() {
  const [rows, setRows] = useState<DriftRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState("");
  const [showDriftOnly, setShowDriftOnly] = useState(true);
  const [page, setPage] = useState(1);
  const pageSize = 10;

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const activeRegistry = await resolveActiveRegistry();

      if (!activeRegistry) {
        setRows([]);
        return;
      }

      const search = await schemaApi.searchSchemas({ limit: 100, page: 1 });
      const driftRows = await Promise.all(
        search.items.map(async (artifact): Promise<DriftRow> => ({
          ...artifact,
          drift: await loadDriftSafely(artifact, activeRegistry.registry_id),
        })),
      );

      setRows(driftRows);
    } catch (error) {
      toast.error(extractErrorMessage(error, "Failed to load drift monitor"));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    setPage(1);
  }, [query, showDriftOnly]);

  const filteredRows = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    return rows.filter((row) => {
      const matchesDrift = !showDriftOnly || row.drift?.has_drift;
      const matchesQuery =
        !normalizedQuery ||
        [row.subject, row.owner, row.compatibility_mode]
          .filter(Boolean)
          .some((value) => value!.toLowerCase().includes(normalizedQuery));
      return matchesDrift && matchesQuery;
    });
  }, [query, rows, showDriftOnly]);

  const pagedRows = useMemo(
    () => filteredRows.slice((page - 1) * pageSize, page * pageSize),
    [filteredRows, page],
  );
  const totalPages = Math.max(1, Math.ceil(filteredRows.length / pageSize));
  const driftCount = rows.filter((row) => row.drift?.has_drift).length;

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loading size="lg" />
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-[1200px] mx-auto">
      <div className="flex items-end justify-between">
        <div>
          <div className="flex items-center gap-2 text-amber-600 font-semibold text-sm mb-1">
            <Radar className="h-4 w-4" />
            Drift Monitoring
          </div>
          <h1 className="text-3xl font-bold text-gray-900 tracking-tight">Schema Drift Monitor</h1>
          <p className="mt-1 text-sm text-gray-500">
            Track registry/catalog mismatches and outdated observed usage across schema subjects.
          </p>
        </div>
        <Button onClick={() => void load()} variant="secondary">
          <RefreshCw className="h-4 w-4" />
          Refresh
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <MetricCard label="Subjects scanned" value={rows.length} accent="text-slate-700" />
        <MetricCard label="Subjects with drift" value={driftCount} accent="text-amber-600" />
        <MetricCard
          label="Observed usage lagging"
          value={rows.filter((row) => row.drift?.drift_flags.includes("observed_usage_on_non_latest_version")).length}
          accent="text-rose-600"
        />
      </div>

      <Card className="overflow-hidden border-gray-200 shadow-sm">
        <CardHeader className="bg-white border-b border-gray-100">
          <CardTitle className="text-lg font-bold flex items-center gap-2">
            <AlertTriangle className="h-5 w-5" />
            Drifted Subjects
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <div className="p-4 border-b border-gray-100 bg-gray-50 grid grid-cols-1 md:grid-cols-[1fr_auto] gap-3">
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search by subject, owner, compatibility..."
              className="rounded-lg border border-gray-200 px-3 py-2 text-sm"
            />
            <label className="flex items-center gap-2 text-sm text-gray-600">
              <input
                type="checkbox"
                checked={showDriftOnly}
                onChange={(event) => setShowDriftOnly(event.target.checked)}
              />
              Show drift only
            </label>
          </div>

          {filteredRows.length === 0 ? (
            <div className="p-6 text-sm text-gray-500">No drift subjects matched the current filters.</div>
          ) : (
            <div className="divide-y divide-gray-100">
              {pagedRows.map((row) => (
                <div key={row.subject} className="p-5 space-y-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-sm font-semibold text-gray-900">{row.subject}</span>
                    <Badge variant={row.drift?.has_drift ? "warning" : "success"} className="uppercase">
                      {row.drift?.has_drift ? "drift" : "in sync"}
                    </Badge>
                    {row.compatibility_mode && (
                      <Badge variant="outline" className="uppercase">
                        {row.compatibility_mode}
                      </Badge>
                    )}
                  </div>
                  <div className="text-xs text-gray-500 flex flex-wrap gap-3">
                    <span>Owner: {row.owner || "Not set"}</span>
                    <span>Catalog version: {row.version ?? "N/A"}</span>
                    <span>Registry latest: {row.drift?.registry_latest_version ?? "N/A"}</span>
                    <span>Observed usage: {row.drift?.observed_version ?? "N/A"}</span>
                  </div>
                  <div className="text-xs text-gray-600">
                    {(row.drift?.drift_flags.length ?? 0) > 0
                      ? row.drift?.drift_flags.join(", ")
                      : "No drift flags recorded."}
                  </div>
                </div>
              ))}
            </div>
          )}

          <div className="px-4 py-3 border-t border-gray-100 bg-white flex items-center justify-between">
            <div className="text-xs text-gray-500">
              Page {page} of {totalPages}
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="secondary"
                onClick={() => setPage((current) => Math.max(1, current - 1))}
                disabled={page === 1}
              >
                Previous
              </Button>
              <Button
                variant="secondary"
                onClick={() => setPage((current) => Math.min(totalPages, current + 1))}
                disabled={page === totalPages}
              >
                Next
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

async function loadDriftSafely(
  artifact: SchemaArtifactResponse,
  registryId: string,
): Promise<SchemaDriftResponse | null> {
  try {
    return await schemaApi.getDrift(artifact.subject, registryId);
  } catch {
    return null;
  }
}

function MetricCard({
  label,
  value,
  accent,
}: {
  label: string;
  value: number;
  accent: string;
}) {
  return (
    <Card>
      <CardContent className="pt-6">
        <div className="text-sm font-medium text-gray-500">{label}</div>
        <div className={`text-3xl font-bold mt-1 ${accent}`}>{value}</div>
      </CardContent>
    </Card>
  );
}
