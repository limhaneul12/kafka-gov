import { useTranslation } from "react-i18next";
import { Server } from "lucide-react";
import { ConnectionCard } from "./ConnectionCard";
import type { KafkaCluster } from "../Connections.types";

interface KafkaClusterListProps {
  clusters: KafkaCluster[];
  onEdit: (cluster: KafkaCluster) => void;
  onDelete: (id: string, name: string) => void;
  onTest: (id: string, name: string) => void;
  onActivate: (id: string) => void;
}

export function KafkaClusterList({
  clusters,
  onEdit,
  onDelete,
  onTest,
  onActivate,
}: KafkaClusterListProps) {
  const { t } = useTranslation();

  if (clusters.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        <p>{t("connection.noConnections")}</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {clusters.map((cluster) => (
        <ConnectionCard
          key={cluster.cluster_id}
          title={cluster.name}
          subtitle={cluster.bootstrap_servers}
          isActive={cluster.is_active}
          icon={<Server className="h-5 w-5" />}
          onEdit={() => onEdit(cluster)}
          onDelete={() => onDelete(cluster.cluster_id, cluster.name)}
          onTest={() => onTest(cluster.cluster_id, cluster.name)}
          onActivate={() => onActivate(cluster.cluster_id)}
        >
          <p>
            <span className="font-medium">Security:</span> {cluster.security_protocol}
          </p>
        </ConnectionCard>
      ))}
    </div>
  );
}
