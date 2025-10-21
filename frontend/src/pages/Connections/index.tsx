import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Plus } from "lucide-react";
import { Card } from "../../components/ui/Card";
import Button from "../../components/ui/Button";
import Loading from "../../components/ui/Loading";
import AddConnectionModal from "../../components/connection/AddConnectionModal";
import { useConnections } from "./hooks/useConnections";
import { KafkaClusterList } from "./components/KafkaClusterList";
import { SchemaRegistryList } from "./components/SchemaRegistryList";
import { StorageList } from "./components/StorageList";
import { KafkaConnectList } from "./components/KafkaConnectList";
import type { ConnectionType } from "./Connections.types";

type TabType = "kafka" | "registry" | "storage" | "connect";

export default function Connections() {
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState<TabType>("kafka");
  const [showAddModal, setShowAddModal] = useState(false);
  const [addType, setAddType] = useState<ConnectionType>("kafka");

  const {
    clusters,
    registries,
    storages,
    connects,
    loading,
    addConnection,
    deleteConnection,
    testConnection,
    activateConnection,
  } = useConnections();

  const handleAddClick = (type: ConnectionType) => {
    setAddType(type);
    setShowAddModal(true);
  };

  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const handleEdit = (_type: ConnectionType, _data: unknown) => {
    // TODO: Implement edit modal
  };

  const tabs = [
    { id: "kafka" as TabType, label: t("connection.broker"), count: clusters.length },
    { id: "registry" as TabType, label: t("connection.registry"), count: registries.length },
    { id: "storage" as TabType, label: t("connection.storage"), count: storages.length },
    { id: "connect" as TabType, label: t("connection.connect"), count: connects.length },
  ];

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
          <h1 className="text-3xl font-bold text-gray-900">{t("connection.list")}</h1>
          <p className="mt-2 text-gray-600">
            {t("connection.description")}
          </p>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="flex gap-8">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`pb-4 px-1 border-b-2 font-medium text-sm transition-colors ${
                activeTab === tab.id
                  ? "border-blue-600 text-blue-600"
                  : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
              }`}
            >
              {tab.label}
              <span className="ml-2 px-2 py-0.5 rounded-full text-xs bg-gray-100">
                {tab.count}
              </span>
            </button>
          ))}
        </nav>
      </div>

      {/* Add Button */}
      <div className="flex justify-end">
        <Button onClick={() => handleAddClick(activeTab)}>
          <Plus className="h-4 w-4" />
          {t("connection.add")}
        </Button>
      </div>

      {/* Content */}
      <Card className="p-6">
        {activeTab === "kafka" && (
          <KafkaClusterList
            clusters={clusters}
            onEdit={(cluster) => handleEdit("kafka", cluster)}
            onDelete={(id, name) => deleteConnection("kafka", id, name)}
            onTest={(id, name) => testConnection("kafka", id, name)}
            onActivate={(id) => activateConnection("kafka", id)}
          />
        )}

        {activeTab === "registry" && (
          <SchemaRegistryList
            registries={registries}
            onEdit={(registry) => handleEdit("registry", registry)}
            onDelete={(id, name) => deleteConnection("registry", id, name)}
            onTest={(id, name) => testConnection("registry", id, name)}
            onActivate={(id) => activateConnection("registry", id)}
          />
        )}

        {activeTab === "storage" && (
          <StorageList
            storages={storages}
            onEdit={(storage) => handleEdit("storage", storage)}
            onDelete={(id, name) => deleteConnection("storage", id, name)}
            onTest={(id, name) => testConnection("storage", id, name)}
            onActivate={(id) => activateConnection("storage", id)}
          />
        )}

        {activeTab === "connect" && (
          <KafkaConnectList
            connects={connects}
            onEdit={(connect) => handleEdit("connect", connect)}
            onDelete={(id, name) => deleteConnection("connect", id, name)}
            onTest={(id, name) => testConnection("connect", id, name)}
            onActivate={(id) => activateConnection("connect", id)}
          />
        )}
      </Card>

      {/* Add Modal */}
      <AddConnectionModal
        isOpen={showAddModal}
        onClose={() => setShowAddModal(false)}
        onSubmit={addConnection}
        defaultType={addType}
      />
    </div>
  );
}
