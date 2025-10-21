import { useTranslation } from "react-i18next";
import { Link } from "lucide-react";
import { ConnectionCard } from "./ConnectionCard";
import type { KafkaConnect } from "../Connections.types";

interface KafkaConnectListProps {
  connects: KafkaConnect[];
  onEdit: (connect: KafkaConnect) => void;
  onDelete: (id: string, name: string) => void;
  onTest: (id: string, name: string) => void;
  onActivate: (id: string) => void;
}

export function KafkaConnectList({
  connects,
  onEdit,
  onDelete,
  onTest,
  onActivate,
}: KafkaConnectListProps) {
  const { t } = useTranslation();

  if (connects.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        <p>{t("connection.noConnections")}</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {connects.map((connect) => (
        <ConnectionCard
          key={connect.connect_id}
          title={connect.name}
          subtitle={connect.url}
          isActive={connect.is_active}
          icon={<Link className="h-5 w-5" />}
          onEdit={() => onEdit(connect)}
          onDelete={() => onDelete(connect.connect_id, connect.name)}
          onTest={() => onTest(connect.connect_id, connect.name)}
          onActivate={() => onActivate(connect.connect_id)}
        />
      ))}
    </div>
  );
}
