import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import { clustersAPI } from "../../../services/api";
import type { KafkaCluster, SchemaRegistry, KafkaConnect } from "../Connections.types";

export function useConnections() {
  const { t } = useTranslation();
  const [clusters, setClusters] = useState<KafkaCluster[]>([]);
  const [registries, setRegistries] = useState<SchemaRegistry[]>([]);
  const [connects, setConnects] = useState<KafkaConnect[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadConnections();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadConnections = async () => {
    try {
      setLoading(true);
      const [clustersRes, registriesRes, connectsRes] = await Promise.all([
        clustersAPI.listKafka(),
        clustersAPI.listRegistries(),
        clustersAPI.listConnects(),
      ]);
      setClusters(clustersRes.data);
      setRegistries(registriesRes.data);
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

  const updateConnection = async (type: string, id: string, data: Record<string, unknown>) => {
    try {
      switch (type) {
        case "kafka":
          await clustersAPI.updateKafka(id, data);
          break;
        case "registry":
          await clustersAPI.updateRegistry(id, data);
          break;
        case "connect":
          await clustersAPI.updateConnect(id, data);
          break;
      }
      await loadConnections();
      toast.success(t("common.success"), {
        description: "Connection updated successfully",
      });
    } catch (error) {
      console.error("Failed to update connection:", error);
      toast.error(t("error.general"), {
        description: "Failed to update connection",
      });
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
      let response;
      switch (type) {
        case "kafka":
          response = await clustersAPI.testKafka(id);
          break;
        case "registry":
          response = await clustersAPI.testRegistry(id);
          break;
        case "connect":
          response = await clustersAPI.testConnect(id);
          break;
      }

      // Backend는 HTTP 200을 반환하지만 success 필드로 실제 연결 성공/실패 판단
      if (response?.data?.success) {
        toast.success(t("connection.test"), {
          description: `"${name}" ${t("dashboard.healthy")} (${response.data.latency_ms?.toFixed(0)}ms)`,
        });
      } else {
        toast.error(t("connection.test"), {
          description: `"${name}" connection failed: ${response?.data?.message || "Unknown error"}`,
        });
      }
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
    connects,
    loading,
    loadConnections,
    addConnection,
    updateConnection,
    deleteConnection,
    testConnection,
    activateConnection,
  };
}
