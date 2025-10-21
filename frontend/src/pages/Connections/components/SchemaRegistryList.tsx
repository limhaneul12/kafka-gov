import { useTranslation } from "react-i18next";
import { Database } from "lucide-react";
import { ConnectionCard } from "./ConnectionCard";
import type { SchemaRegistry } from "../Connections.types";

interface SchemaRegistryListProps {
  registries: SchemaRegistry[];
  onEdit: (registry: SchemaRegistry) => void;
  onDelete: (id: string, name: string) => void;
  onTest: (id: string, name: string) => void;
  onActivate: (id: string) => void;
}

export function SchemaRegistryList({
  registries,
  onEdit,
  onDelete,
  onTest,
  onActivate,
}: SchemaRegistryListProps) {
  const { t } = useTranslation();

  if (registries.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        <p>{t("connection.noConnections")}</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {registries.map((registry) => (
        <ConnectionCard
          key={registry.registry_id}
          title={registry.name}
          subtitle={registry.url}
          isActive={registry.is_active}
          icon={<Database className="h-5 w-5" />}
          onEdit={() => onEdit(registry)}
          onDelete={() => onDelete(registry.registry_id, registry.name)}
          onTest={() => onTest(registry.registry_id, registry.name)}
          onActivate={() => onActivate(registry.registry_id)}
        />
      ))}
    </div>
  );
}
