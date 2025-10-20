import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/Card";
import Button from "../components/ui/Button";
import Badge from "../components/ui/Badge";
import Loading from "../components/ui/Loading";
import CreateConnectorModal from "../components/connect/CreateConnectorModal";
import ConnectorDetailModal from "../components/connect/ConnectorDetailModal";
import PluginsModal from "../components/connect/PluginsModal";
import ValidateConfigModal from "../components/connect/ValidateConfigModal";
import { connectAPI, clustersAPI } from "../services/api";
import {
  Plus,
  RefreshCw,
  Play,
  Pause,
  RotateCw,
  Trash2,
  Activity,
  Server,
  AlertCircle,
  Eye,
  Package,
} from "lucide-react";
import type { ConnectorStatus, KafkaConnect } from "../types";
import { toast } from "sonner";

export default function Connect() {
  const [connects, setConnects] = useState<KafkaConnect[]>([]);
  const [selectedConnect, setSelectedConnect] = useState<string>("");
  const [connectors, setConnectors] = useState<ConnectorStatus[]>([]);
  const [loading, setLoading] = useState(true);
  const [metricsLoading, setMetricsLoading] = useState(false);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showDetailModal, setShowDetailModal] = useState(false);
  const [showPluginsModal, setShowPluginsModal] = useState(false);
  const [showValidateModal, setShowValidateModal] = useState(false);
  const [selectedConnectorName, setSelectedConnectorName] = useState<string>("");
  const [selectedPluginClass, setSelectedPluginClass] = useState<string>("");

  useEffect(() => {
    loadConnects();
  }, []);

  useEffect(() => {
    if (selectedConnect) {
      loadConnectors();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedConnect]);

  const loadConnects = async () => {
    try {
      const response = await clustersAPI.listConnects();
      setConnects(response.data);
      if (response.data.length > 0) {
        setSelectedConnect(response.data[0].connect_id);
      }
    } catch (error) {
      console.error("Failed to load connects:", error);
    } finally {
      setLoading(false);
    }
  };

  const loadConnectors = async () => {
    if (!selectedConnect) return;

    try {
      setMetricsLoading(true);
      const response = await connectAPI.list(selectedConnect);
      setConnectors(response.data || []);
    } catch (error) {
      console.error("Failed to load connectors:", error);
    } finally {
      setMetricsLoading(false);
    }
  };

  const handlePause = async (name: string) => {
    try {
      await connectAPI.pause(selectedConnect, name);
      await loadConnectors();
      toast.success('일시정지 완료', {
        description: `커넥터 "${name}"이(가) 일시정지되었습니다.`
      });
    } catch (error) {
      console.error("Failed to pause connector:", error);
      toast.error('일시정지 실패', {
        description: '커넥터 일시정지에 실패했습니다.'
      });
    }
  };

  const handleResume = async (name: string) => {
    try {
      await connectAPI.resume(selectedConnect, name);
      await loadConnectors();
      toast.success('재개 완료', {
        description: `커넥터 "${name}"이(가) 재개되었습니다.`
      });
    } catch (error) {
      console.error("Failed to resume connector:", error);
      toast.error('재개 실패', {
        description: '커넥터 재개에 실패했습니다.'
      });
    }
  };

  const handleRestart = async (name: string) => {
    if (!confirm(`Restart connector "${name}"?`)) return;

    try {
      await connectAPI.restart(selectedConnect, name);
      await loadConnectors();
      toast.success('재시작 완료', {
        description: `커넥터 "${name}"이(가) 재시작되었습니다.`
      });
    } catch (error) {
      console.error("Failed to restart connector:", error);
      toast.error('재시작 실패', {
        description: '커넥터 재시작에 실패했습니다.'
      });
    }
  };

  const handleDelete = async (name: string) => {
    if (!confirm(`Delete connector "${name}"? This action cannot be undone.`)) {
      return;
    }

    try {
      await connectAPI.delete(selectedConnect, name);
      await loadConnectors();
      toast.success('삭제 완료', {
        description: `커넥터 "${name}"이(가) 삭제되었습니다.`
      });
    } catch (error) {
      console.error("Failed to delete connector:", error);
      toast.error('삭제 실패', {
        description: '커넥터 삭제에 실패했습니다.'
      });
    }
  };

  const handleCreateConnector = async (config: { name: string; config: Record<string, string | number> }) => {
    await connectAPI.create(selectedConnect, config);
    await loadConnectors();
  };

  const handleViewDetails = (name: string) => {
    setSelectedConnectorName(name);
    setShowDetailModal(true);
  };

  const handleSelectPlugin = (pluginClass: string) => {
    setSelectedPluginClass(pluginClass);
    setShowValidateModal(true);
  };

  const getStatusBadgeVariant = (state: string) => {
    switch (state?.toUpperCase()) {
      case "RUNNING":
        return "success";
      case "PAUSED":
        return "warning";
      case "FAILED":
        return "danger";
      case "UNASSIGNED":
        return "default";
      default:
        return "default";
    }
  };

  const runningCount = connectors.filter((c) => c.connector.state === "RUNNING").length;
  const pausedCount = connectors.filter((c) => c.connector.state === "PAUSED").length;
  const failedCount = connectors.filter((c) => c.connector.state === "FAILED").length;

  if (loading) {
    return (
      <div className="flex h-96 items-center justify-center">
        <Loading size="lg" />
      </div>
    );
  }

  if (!selectedConnect) {
    return (
      <div className="flex h-96 items-center justify-center">
        <div className="text-center">
          <Server className="h-16 w-16 text-gray-400 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-gray-900 mb-2">
            Kafka Connect가 설정되지 않았습니다
          </h2>
          <p className="text-gray-600">
            설정 페이지에서 Kafka Connect를 먼저 등록해주세요.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Kafka Connect</h1>
          <p className="mt-2 text-gray-600">커넥터를 관리하고 모니터링합니다</p>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={loadConnectors}>
            <RefreshCw className="h-4 w-4" />
            Refresh
          </Button>
          <Button variant="secondary" onClick={() => setShowPluginsModal(true)}>
            <Package className="h-4 w-4" />
            View Plugins
          </Button>
          <Button onClick={() => setShowCreateModal(true)}>
            <Plus className="h-4 w-4" />
            Add Connector
          </Button>
        </div>
      </div>

      {/* Connect Selection */}
      <Card>
        <CardContent className="pt-6">
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Kafka Connect
              </label>
              <select
                value={selectedConnect}
                onChange={(e) => setSelectedConnect(e.target.value)}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                {connects.map((conn) => (
                  <option key={conn.connect_id} value={conn.connect_id}>
                    {conn.name} ({conn.url})
                  </option>
                ))}
              </select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Metrics Cards */}
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Total Connectors</p>
                <p className="mt-2 text-3xl font-bold text-gray-900">
                  {connectors.length}
                </p>
              </div>
              <div className="rounded-full bg-blue-100 p-3">
                <Activity className="h-6 w-6 text-blue-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Running</p>
                <p className="mt-2 text-3xl font-bold text-green-600">{runningCount}</p>
              </div>
              <div className="rounded-full bg-green-100 p-3">
                <Play className="h-6 w-6 text-green-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Paused</p>
                <p className="mt-2 text-3xl font-bold text-yellow-600">{pausedCount}</p>
              </div>
              <div className="rounded-full bg-yellow-100 p-3">
                <Pause className="h-6 w-6 text-yellow-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Failed</p>
                <p className="mt-2 text-3xl font-bold text-red-600">{failedCount}</p>
              </div>
              <div className="rounded-full bg-red-100 p-3">
                <AlertCircle className="h-6 w-6 text-red-600" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Connectors Table */}
      <Card>
        <CardHeader>
          <CardTitle>Connectors ({connectors.length})</CardTitle>
        </CardHeader>
        <CardContent>
          {metricsLoading ? (
            <Loading />
          ) : (
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
                      Status
                    </th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">
                      Tasks
                    </th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">
                      Worker
                    </th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {connectors.length === 0 ? (
                    <tr>
                      <td
                        colSpan={6}
                        className="px-4 py-8 text-center text-gray-500"
                      >
                        No connectors found
                      </td>
                    </tr>
                  ) : (
                    connectors.map((connector) => (
                      <tr key={connector.name} className="hover:bg-gray-50">
                        <td className="px-4 py-3 text-sm font-medium text-gray-900">
                          {connector.name}
                        </td>
                        <td className="px-4 py-3">
                          <Badge variant="info">{connector.type}</Badge>
                        </td>
                        <td className="px-4 py-3">
                          <Badge
                            variant={getStatusBadgeVariant(
                              connector.connector.state
                            )}
                          >
                            {connector.connector.state}
                          </Badge>
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-600">
                          {connector.tasks.length} tasks
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-600">
                          {connector.connector.worker_id}
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex gap-1">
                            {connector.connector.state === "RUNNING" ? (
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => handlePause(connector.name)}
                                title="Pause"
                              >
                                <Pause className="h-4 w-4 text-yellow-600" />
                              </Button>
                            ) : (
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => handleResume(connector.name)}
                                title="Resume"
                              >
                                <Play className="h-4 w-4 text-green-600" />
                              </Button>
                            )}
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => handleRestart(connector.name)}
                              title="Restart"
                            >
                              <RotateCw className="h-4 w-4 text-blue-600" />
                            </Button>
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => handleDelete(connector.name)}
                              title="Delete"
                            >
                              <Trash2 className="h-4 w-4 text-red-600" />
                            </Button>
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => handleViewDetails(connector.name)}
                              title="View Details"
                            >
                              <Eye className="h-4 w-4 text-gray-600" />
                            </Button>
                          </div>
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

      {/* Modals */}
      <CreateConnectorModal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        onSubmit={handleCreateConnector}
        connectId={selectedConnect}
      />

      {selectedConnectorName && (
        <ConnectorDetailModal
          isOpen={showDetailModal}
          onClose={() => {
            setShowDetailModal(false);
            setSelectedConnectorName("");
          }}
          connectId={selectedConnect}
          connectorName={selectedConnectorName}
        />
      )}

      <PluginsModal
        isOpen={showPluginsModal}
        onClose={() => setShowPluginsModal(false)}
        connectId={selectedConnect}
        onSelectPlugin={handleSelectPlugin}
      />

      {selectedPluginClass && (
        <ValidateConfigModal
          isOpen={showValidateModal}
          onClose={() => {
            setShowValidateModal(false);
            setSelectedPluginClass("");
          }}
          connectId={selectedConnect}
          pluginClass={selectedPluginClass}
        />
      )}
    </div>
  );
}
