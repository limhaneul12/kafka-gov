import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Plus } from "lucide-react";

import AddConnectionModal from "../../components/connection/AddConnectionModal";
import { Card } from "../../components/ui/Card";
import Button from "../../components/ui/Button";
import Loading from "../../components/ui/Loading";
import { SchemaRegistryList } from "./components/SchemaRegistryList";
import { useConnections } from "./hooks/useConnections";

export default function Connections() {
  const { t } = useTranslation();
  const [showAddModal, setShowAddModal] = useState(false);
  const [editMode, setEditMode] = useState(false);
  const [editData, setEditData] = useState<Record<string, unknown> | undefined>();

  const {
    registries,
    loading,
    addConnection,
    updateConnection,
    deleteConnection,
    testConnection,
    activateConnection,
  } = useConnections();

  const handleEdit = (data: unknown) => {
    setEditMode(true);
    setEditData(data as Record<string, unknown>);
    setShowAddModal(true);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loading size="lg" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">{t("connection.list")}</h1>
          <p className="mt-2 text-gray-600">Schema Registry connections used by the schema governance workflow.</p>
        </div>
      </div>

      <div className="flex justify-end">
        <Button onClick={() => setShowAddModal(true)}>
          <Plus className="h-4 w-4" />
          {t("connection.add")}
        </Button>
      </div>

      <Card className="p-6">
        <SchemaRegistryList
          registries={registries}
          onEdit={handleEdit}
          onDelete={(id, name) => deleteConnection(id, name)}
          onTest={(id, name) => testConnection(id, name)}
          onActivate={(id) => activateConnection(id)}
        />
      </Card>

      <AddConnectionModal
        isOpen={showAddModal}
        onClose={() => {
          setShowAddModal(false);
          setEditMode(false);
          setEditData(undefined);
        }}
        onSubmit={addConnection}
        onUpdate={updateConnection}
        editMode={editMode}
        initialData={editData}
      />
    </div>
  );
}
