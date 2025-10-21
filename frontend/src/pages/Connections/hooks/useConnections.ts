import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import { clustersAPI } from "../../../services/api";
import type { KafkaCluster, SchemaRegistry, ObjectStorage, KafkaConnect } from "../Connections.types";

export function useConnections() {
  const { t } = useTranslation();
  const [clusters, setClusters] = useState<KafkaCluster[]>([]);
  const [registries, setRegistries] = useState<SchemaRegistry[]>([]);
  const [storages, setStorages] = useState<ObjectStorage[]>([]);
  const [connects, setConnects] = useState<KafkaConnect[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadConnections();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadConnections = async () => {
    try {
      setLoading(true);
      const [clustersRes, registriesRes, storagesRes, connectsRes] = await Promise.all([
        clustersAPI.listKafka(),
        clustersAPI.listRegistries(),
        clustersAPI.listStorages(),
        clustersAPI.listConnects(),
      ]);
      setClusters(clustersRes.data);
      setRegistries(registriesRes.data);
      setStorages(storagesRes.data);
      setConnects(connectsRes.data);
    } catch (error) {
      console.error("Failed to load connections:", error);
      toast.error(t("error.general"));
    } finally {
      setLoading(false);
    }
  };

  const addConnection = async (type: string, data: Record<string, string>) => {
    try {
      switch (type) {
        case "kafka":
          await clustersAPI.createKafka(data);
          break;
        case "registry":
          await clustersAPI.createRegistry(data);
          break;
        case "storage":
          await clustersAPI.createStorage(data);
          break;
        case "connect":
          await clustersAPI.createConnect(data);
          break;
      }
      await loadConnections();
      toast.success(t("common.success"));
    } catch (error) {
      console.error("Failed to add connection:", error);
      throw error;
    }
  };

  const deleteConnection = async (type: string, id: string, name: string) => {
    if (!confirm(`Delete "${name}"?`)) return;

    try {
      switch (type) {
        case "kafka":
          await clustersAPI.deleteKafka(id);
          break;
        case "registry":
          await clustersAPI.deleteRegistry(id);
          break;
        case "storage":
          await clustersAPI.deleteStorage(id);
          break;
        case "connect":
          await clustersAPI.deleteConnect(id);
          break;
      }
      await loadConnections();
      toast.success(t("common.success"));
    } catch (error) {
      console.error("Failed to delete connection:", error);
      toast.error(t("error.general"));
    }
  };

  const testConnection = async (type: string, id: string, name: string) => {
    try {
      switch (type) {
        case "kafka":
          await clustersAPI.testKafka(id);
          break;
        case "registry":
          await clustersAPI.testRegistry(id);
          break;
        case "storage":
          await clustersAPI.testStorage(id);
          break;
        case "connect":
          await clustersAPI.testConnect(id);
          break;
      }
      toast.success(t("connection.test"), {
        description: `"${name}" ${t("dashboard.healthy")}`,
      });
    } catch (error) {
      console.error("Failed to test connection:", error);
      toast.error(t("error.network"), {
        description: `"${name}" ${t("connection.test")} failed`,
      });
    }
  };

  const activateConnection = async (type: string, id: string) => {
    try {
      // Backend에 PATCH /{id}/activate 엔드포인트 사용
      // is_active만 true로 변경하고 나머지는 기존 값 유지
      
      switch (type) {
        case "kafka":
          await clustersAPI.activateKafka(id);
          break;
        case "registry":
          await clustersAPI.activateRegistry(id);
          break;
        case "storage":
          await clustersAPI.activateStorage(id);
          break;
        case "connect":
          await clustersAPI.activateConnect(id);
          break;
      }
      
      await loadConnections();
      toast.success(t("common.success"), {
        description: "Connection activated successfully",
      });
    } catch (error) {
      console.error("Failed to activate connection:", error);
      toast.error(t("error.general"), {
        description: "Failed to activate connection",
      });
    }
  };

  return {
    clusters,
    registries,
    storages,
    connects,
    loading,
    loadConnections,
    addConnection,
    deleteConnection,
    testConnection,
    activateConnection,
  };
}
