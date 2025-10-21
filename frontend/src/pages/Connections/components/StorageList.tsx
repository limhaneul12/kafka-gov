import { useTranslation } from "react-i18next";
import { HardDrive } from "lucide-react";
import { ConnectionCard } from "./ConnectionCard";
import type { ObjectStorage } from "../Connections.types";

interface StorageListProps {
  storages: ObjectStorage[];
  onEdit: (storage: ObjectStorage) => void;
  onDelete: (id: string, name: string) => void;
  onTest: (id: string, name: string) => void;
  onActivate: (id: string) => void;
}

export function StorageList({
  storages,
  onEdit,
  onDelete,
  onTest,
  onActivate,
}: StorageListProps) {
  const { t } = useTranslation();

  if (storages.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        <p>{t("connection.noConnections")}</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {storages.map((storage) => (
        <ConnectionCard
          key={storage.storage_id}
          title={storage.name}
          subtitle={storage.endpoint}
          isActive={storage.is_active}
          icon={<HardDrive className="h-5 w-5" />}
          onEdit={() => onEdit(storage)}
          onDelete={() => onDelete(storage.storage_id, storage.name)}
          onTest={() => onTest(storage.storage_id, storage.name)}
          onActivate={() => onActivate(storage.storage_id)}
        >
          <p>
            <span className="font-medium">Bucket:</span> {storage.bucket}
          </p>
        </ConnectionCard>
      ))}
    </div>
  );
}
