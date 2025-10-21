import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Plus, RefreshCw, Server, Package } from "lucide-react";
import { Card } from "../../components/ui/Card";
import Button from "../../components/ui/Button";
import Loading from "../../components/ui/Loading";
import CreateConnectorModal from "../../components/connect/CreateConnectorModal";
import ConnectorDetailModal from "../../components/connect/ConnectorDetailModal";
import PluginsModal from "../../components/connect/PluginsModal";
import { useConnectors } from "./hooks/useConnectors";
import { ConnectorCard } from "./components/ConnectorCard";

export default function Connect() {
  const { t } = useTranslation();
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showDetailModal, setShowDetailModal] = useState(false);
  const [showPluginsModal, setShowPluginsModal] = useState(false);
  const [selectedConnectorName, setSelectedConnectorName] = useState("");
  const [selectedPluginClass, setSelectedPluginClass] = useState<string | undefined>(undefined);

  const {
    connects,
    selectedConnect,
    setSelectedConnect,
    connectors,
    loading,
    metricsLoading,
    loadConnectors,
    pauseConnector,
    resumeConnector,
    restartConnector,
    deleteConnector,
  } = useConnectors();

  const handleViewDetails = (name: string) => {
    setSelectedConnectorName(name);
    setShowDetailModal(true);
  };

  // Kafka Connect 연결 없음
  if (!loading && connects.length === 0) {
    return (
      <div className="flex h-96 items-center justify-center">
        <div className="text-center">
          <Server className="h-16 w-16 text-gray-400 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-gray-900 mb-2">
            {t("connect.notConfigured")}
          </h2>
          <p className="text-gray-600">
            {t("connect.pleaseConfigureFirst")}
          </p>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loading size="lg" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">{t("connect.list")}</h1>
          <p className="mt-2 text-gray-600">
            Manage Kafka Connect connectors and monitor their status
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="secondary" onClick={() => setShowPluginsModal(true)}>
            <Package className="h-4 w-4" />
            Plugins
          </Button>
          <Button onClick={() => setShowCreateModal(true)}>
            <Plus className="h-4 w-4" />
            {t("connect.create")}
          </Button>
        </div>
      </div>

      {/* Connect Cluster Selector */}
      {connects.length > 0 && (
        <Card className="p-4">
          <div className="flex items-center gap-4">
            <Server className="h-5 w-5 text-gray-500" />
            <label className="text-sm font-medium text-gray-700">
              Kafka Connect Cluster:
            </label>
            <select
              value={selectedConnect}
              onChange={(e) => setSelectedConnect(e.target.value)}
              className="rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              {connects.map((connect) => (
                <option key={connect.connect_id} value={connect.connect_id}>
                  {connect.name} ({connect.url})
                </option>
              ))}
            </select>
            <Button variant="secondary" size="sm" onClick={loadConnectors}>
              <RefreshCw className={`h-4 w-4 ${metricsLoading ? "animate-spin" : ""}`} />
            </Button>
          </div>
        </Card>
      )}

      {/* Connectors List */}
      <Card className="p-6">
        {metricsLoading ? (
          <div className="flex items-center justify-center h-64">
            <Loading size="lg" />
          </div>
        ) : connectors.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            <p>{t("connect.noConnectors")}</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {connectors.map((connector) => (
              <ConnectorCard
                key={connector.name}
                connector={connector}
                onPause={() => pauseConnector(connector.name)}
                onResume={() => resumeConnector(connector.name)}
                onRestart={() => restartConnector(connector.name)}
                onDelete={() => deleteConnector(connector.name)}
                onViewDetails={() => handleViewDetails(connector.name)}
              />
            ))}
          </div>
        )}
      </Card>

      {/* Modals */}
      <CreateConnectorModal
        isOpen={showCreateModal}
        onClose={() => {
          setShowCreateModal(false);
          setSelectedPluginClass(undefined);
        }}
        connectId={selectedConnect}
        selectedPluginClass={selectedPluginClass}
        onSubmit={async () => {
          await loadConnectors();
        }}
      />

      {showDetailModal && (
        <ConnectorDetailModal
          isOpen={showDetailModal}
          onClose={() => setShowDetailModal(false)}
          connectId={selectedConnect}
          connectorName={selectedConnectorName}
        />
      )}

      <PluginsModal
        isOpen={showPluginsModal}
        onClose={() => setShowPluginsModal(false)}
        connectId={selectedConnect}
        onSelectPlugin={(pluginClass) => {
          setSelectedPluginClass(pluginClass);
          setShowPluginsModal(false);
          setShowCreateModal(true);
        }}
      />
    </div>
  );
}
