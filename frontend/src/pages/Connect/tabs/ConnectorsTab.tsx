import { useState } from "react";
import { Plus, Search } from "lucide-react";
import { Card } from "../../../components/ui/Card";
import Button from "../../../components/ui/Button";
import Loading from "../../../components/ui/Loading";
import { ConnectorCard } from "../components/ConnectorCard";
import type { ConnectorStatus } from "../Connect.types";

interface ConnectorsTabProps {
  connectors: ConnectorStatus[];
  loading: boolean;
  onPause: (name: string) => void;
  onResume: (name: string) => void;
  onRestart: (name: string) => void;
  onDelete: (name: string) => void;
  onViewDetails: (name: string) => void;
  onCreateClick: () => void;
}

export function ConnectorsTab({
  connectors,
  loading,
  onPause,
  onResume,
  onRestart,
  onDelete,
  onViewDetails,
  onCreateClick,
}: ConnectorsTabProps) {
  const [searchTerm, setSearchTerm] = useState("");
  const [typeFilter, setTypeFilter] = useState<"all" | "source" | "sink">("all");
  const [stateFilter, setStateFilter] = useState<"all" | "RUNNING" | "PAUSED" | "FAILED">("all");

  const filteredConnectors = connectors.filter((connector) => {
    const matchesSearch = connector.name.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesType = typeFilter === "all" || connector.type === typeFilter;
    const matchesState = stateFilter === "all" || connector.state === stateFilter;
    return matchesSearch && matchesType && matchesState;
  });

  return (
    <div className="space-y-6">
      {/* Actions Bar */}
      <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
        <div className="flex-1 w-full sm:max-w-md">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search connectors..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
        </div>

        <div className="flex gap-2 flex-wrap">
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value as typeof typeFilter)}
            className="px-3 py-2 border border-gray-300 rounded-lg focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            <option value="all">All Types</option>
            <option value="source">Source</option>
            <option value="sink">Sink</option>
          </select>

          <select
            value={stateFilter}
            onChange={(e) => setStateFilter(e.target.value as typeof stateFilter)}
            className="px-3 py-2 border border-gray-300 rounded-lg focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            <option value="all">All States</option>
            <option value="RUNNING">Running</option>
            <option value="PAUSED">Paused</option>
            <option value="FAILED">Failed</option>
          </select>

          <Button onClick={onCreateClick}>
            <Plus className="h-4 w-4" />
            Add Connector
          </Button>
        </div>
      </div>

      {/* Connectors Grid */}
      <Card className="p-6">
        {loading ? (
          <div className="flex items-center justify-center h-64">
            <Loading size="lg" />
          </div>
        ) : filteredConnectors.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-gray-500">
              {searchTerm || typeFilter !== "all" || stateFilter !== "all"
                ? "No connectors match your filters"
                : "No connectors found. Create your first connector to get started."}
            </p>
          </div>
        ) : (
          <>
            <div className="mb-4 text-sm text-gray-600">
              Showing {filteredConnectors.length} of {connectors.length} connectors
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {filteredConnectors.map((connector) => (
                <ConnectorCard
                  key={connector.name}
                  connector={connector}
                  onPause={() => onPause(connector.name)}
                  onResume={() => onResume(connector.name)}
                  onRestart={() => onRestart(connector.name)}
                  onDelete={() => onDelete(connector.name)}
                  onViewDetails={() => onViewDetails(connector.name)}
                />
              ))}
            </div>
          </>
        )}
      </Card>
    </div>
  );
}
