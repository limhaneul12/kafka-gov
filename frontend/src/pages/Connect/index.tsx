import { useState } from "react";
import { useTranslation } from "react-i18next";
import { RefreshCw, Server, LayoutDashboard, Cable, ListTodo, Package } from "lucide-react";
import { Card } from "../../components/ui/Card";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "../../components/ui/Tabs";
import Button from "../../components/ui/Button";
import Loading from "../../components/ui/Loading";
import CreateConnectorModal from "../../components/connect/CreateConnectorModal";
import ConnectorDetailModal from "../../components/connect/ConnectorDetailModal";
import { useConnectors } from "./hooks/useConnectors";
import { OverviewTab } from "./tabs/OverviewTab";
import { ConnectorsTab } from "./tabs/ConnectorsTab";
import { TasksTab } from "./tabs/TasksTab";
import { PluginsTab } from "./tabs/PluginsTab";

export default function Connect() {
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState("overview");
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showDetailModal, setShowDetailModal] = useState(false);
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

  const handleSelectPlugin = (pluginClass: string) => {
    setSelectedPluginClass(pluginClass);
    setShowCreateModal(true);
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
          <h1 className="text-3xl font-bold text-gray-900">Kafka Connect</h1>
          <p className="mt-2 text-gray-600">
            Manage Kafka Connect connectors and monitor their status
          </p>
        </div>
        <Button variant="secondary" size="sm" onClick={loadConnectors}>
          <RefreshCw className={`h-4 w-4 ${metricsLoading ? "animate-spin" : ""}`} />
          Refresh
        </Button>
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
              className="flex-1 max-w-md rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              {connects.map((connect) => (
                <option key={connect.connect_id} value={connect.connect_id}>
                  {connect.name} ({connect.url})
                </option>
              ))}
            </select>
          </div>
        </Card>
      )}

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="overview">
            <LayoutDashboard className="h-4 w-4 mr-2" />
            Overview
          </TabsTrigger>
          <TabsTrigger value="connectors">
            <Cable className="h-4 w-4 mr-2" />
            Connectors
          </TabsTrigger>
          <TabsTrigger value="tasks">
            <ListTodo className="h-4 w-4 mr-2" />
            Tasks
          </TabsTrigger>
          <TabsTrigger value="plugins">
            <Package className="h-4 w-4 mr-2" />
            Plugins
          </TabsTrigger>
        </TabsList>

        <TabsContent value="overview">
          <OverviewTab connectors={connectors} loading={metricsLoading} />
        </TabsContent>

        <TabsContent value="connectors">
          <ConnectorsTab
            connectors={connectors}
            loading={metricsLoading}
            onPause={pauseConnector}
            onResume={resumeConnector}
            onRestart={restartConnector}
            onDelete={deleteConnector}
            onViewDetails={handleViewDetails}
            onCreateClick={() => setShowCreateModal(true)}
          />
        </TabsContent>

        <TabsContent value="tasks">
          <TasksTab
            connectors={connectors}
            connectId={selectedConnect}
            loading={metricsLoading}
          />
        </TabsContent>

        <TabsContent value="plugins">
          <PluginsTab
            connectId={selectedConnect}
            onSelectPlugin={handleSelectPlugin}
          />
        </TabsContent>
      </Tabs>

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
    </div>
  );
}
