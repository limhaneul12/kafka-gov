import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";

import { registryAPI } from "../../../services/api";
import type { SchemaRegistry } from "../Connections.types";

export function useConnections() {
  const { t } = useTranslation();
  const [registries, setRegistries] = useState<SchemaRegistry[]>([]);
  const [loading, setLoading] = useState(true);

  const loadConnections = useCallback(async () => {
    try {
      setLoading(true);
      const registriesRes = await registryAPI.list();
      setRegistries(registriesRes.data);
    } catch (error) {
      console.error("Failed to load registry connections:", error);
      toast.error(t("error.general"));
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    void loadConnections();
  }, [loadConnections]);

  const addConnection = async (data: Record<string, string>) => {
    try {
      await registryAPI.create(data);
      await loadConnections();
      toast.success(t("common.success"));
    } catch (error) {
      console.error("Failed to add registry connection:", error);
      throw error;
    }
  };

  const updateConnection = async (id: string, data: Record<string, unknown>) => {
    try {
      await registryAPI.update(id, data);
      await loadConnections();
      toast.success(t("common.success"), {
        description: "Schema Registry connection updated successfully",
      });
    } catch (error) {
      console.error("Failed to update registry connection:", error);
      toast.error(t("error.general"), {
        description: "Failed to update Schema Registry connection",
      });
      throw error;
    }
  };

  const deleteConnection = async (id: string, name: string) => {
    if (!confirm(`Delete "${name}"?`)) return;

    try {
      await registryAPI.delete(id);
      await loadConnections();
      toast.success(t("common.success"));
    } catch (error) {
      console.error("Failed to delete registry connection:", error);
      toast.error(t("error.general"));
    }
  };

  const testConnection = async (id: string, name: string) => {
    try {
      const response = await registryAPI.test(id);
      if (response.data?.success) {
        toast.success(t("connection.test"), {
          description: `"${name}" ${t("dashboard.healthy")} (${response.data.latency_ms?.toFixed(0)}ms)`,
        });
      } else {
        toast.error(t("connection.test"), {
          description: `"${name}" connection failed: ${response.data?.message || "Unknown error"}`,
        });
      }
    } catch (error) {
      console.error("Failed to test registry connection:", error);
      toast.error(t("error.network"), {
        description: `"${name}" ${t("connection.test")} failed`,
      });
    }
  };

  const activateConnection = async (id: string) => {
    try {
      await registryAPI.activate(id);
      await loadConnections();
      toast.success(t("common.success"), {
        description: "Schema Registry connection activated successfully",
      });
    } catch (error) {
      console.error("Failed to activate registry connection:", error);
      toast.error(t("error.general"), {
        description: "Failed to activate Schema Registry connection",
      });
    }
  };

  return {
    registries,
    loading,
    loadConnections,
    addConnection,
    updateConnection,
    deleteConnection,
    testConnection,
    activateConnection,
  };
}
