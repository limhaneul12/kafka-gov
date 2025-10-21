import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import { connectAPI, clustersAPI } from "../../../services/api";
import type { KafkaConnect, ConnectorStatus } from "../Connect.types";

export function useConnectors() {
  const { t } = useTranslation();
  const [connects, setConnects] = useState<KafkaConnect[]>([]);
  const [selectedConnect, setSelectedConnect] = useState<string>("");
  const [connectors, setConnectors] = useState<ConnectorStatus[]>([]);
  const [loading, setLoading] = useState(true);
  const [metricsLoading, setMetricsLoading] = useState(false);

  useEffect(() => {
    loadConnects();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (selectedConnect) {
      loadConnectors();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedConnect]);

  const loadConnects = async () => {
    try {
      const response = await clustersAPI.listConnects();
      setConnects(response.data);
      if (response.data.length > 0) {
        setSelectedConnect(response.data[0].connect_id);
      }
    } catch (error) {
      console.error("Failed to load connects:", error);
      toast.error(t("error.general"));
    } finally {
      setLoading(false);
    }
  };

  const loadConnectors = async () => {
    if (!selectedConnect) return;

    try {
      setMetricsLoading(true);
      const response = await connectAPI.list(selectedConnect);
      setConnectors(response.data || []);
    } catch (error) {
      console.error("Failed to load connectors:", error);
      toast.error(t("error.network"));
    } finally {
      setMetricsLoading(false);
    }
  };

  const pauseConnector = async (name: string) => {
    try {
      await connectAPI.pause(selectedConnect, name);
      await loadConnectors();
      toast.success(t("common.success"));
    } catch (error) {
      console.error("Failed to pause connector:", error);
      toast.error(t("error.general"));
    }
  };

  const resumeConnector = async (name: string) => {
    try {
      await connectAPI.resume(selectedConnect, name);
      await loadConnectors();
      toast.success(t("common.success"));
    } catch (error) {
      console.error("Failed to resume connector:", error);
      toast.error(t("error.general"));
    }
  };

  const restartConnector = async (name: string) => {
    try {
      await connectAPI.restart(selectedConnect, name);
      await loadConnectors();
      toast.success(t("common.success"));
    } catch (error) {
      console.error("Failed to restart connector:", error);
      toast.error(t("error.general"));
    }
  };

  const deleteConnector = async (name: string) => {
    if (!confirm(`Delete connector "${name}"?`)) return;

    try {
      await connectAPI.delete(selectedConnect, name);
      await loadConnectors();
      toast.success(t("common.success"));
    } catch (error) {
      console.error("Failed to delete connector:", error);
      toast.error(t("error.general"));
    }
  };

  return {
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
  };
}
