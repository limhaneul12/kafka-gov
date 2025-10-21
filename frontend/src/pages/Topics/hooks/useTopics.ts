import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import { topicsAPI, clustersAPI } from "../../../services/api";
import type { Topic } from "../Topics.types";

interface KafkaCluster {
  cluster_id: string;
  name: string;
}

export function useTopics() {
  const { t } = useTranslation();
  const [topics, setTopics] = useState<Topic[]>([]);
  const [clusters, setClusters] = useState<KafkaCluster[]>([]);
  const [selectedCluster, setSelectedCluster] = useState<string>("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadClusters();
  }, []);

  useEffect(() => {
    if (selectedCluster) {
      loadTopics();
    }
  }, [selectedCluster]);

  const loadClusters = async () => {
    try {
      const response = await clustersAPI.listKafka();
      setClusters(response.data);
      if (response.data.length > 0) {
        setSelectedCluster(response.data[0].cluster_id);
      }
    } catch (error) {
      console.error("Failed to load clusters:", error);
      toast.error(t("error.general"), {
        description: t("error.network"),
      });
    }
  };

  const loadTopics = async () => {
    if (!selectedCluster) return;

    try {
      setLoading(true);
      const response = await topicsAPI.list(selectedCluster);
      setTopics(response.data.topics || []);
    } catch (error) {
      console.error("Failed to load topics:", error);
      toast.error(t("error.general"), {
        description: t("error.network"),
      });
    } finally {
      setLoading(false);
    }
  };

  const deleteTopic = async (topicName: string) => {
    if (!selectedCluster) return;

    try {
      await topicsAPI.delete(selectedCluster, topicName);
      await loadTopics();
      toast.success(t("common.success"), {
        description: t("topic.delete"),
      });
    } catch (error) {
      console.error("Failed to delete topic:", error);
      toast.error(t("topic.deleteFailed"), {
        description:
          error instanceof Error ? error.message : t("topic.deleteError"),
      });
    }
  };

  const updateMetadata = async (
    topicName: string,
    data: {
      owners: string[];
      doc: string | null;
      tags: string[];
      environment: string;
      slo: string | null;
      sla: string | null;
    }
  ) => {
    if (!selectedCluster) return;

    try {
      await topicsAPI.updateMetadata(selectedCluster, topicName, data);
      await loadTopics();
      toast.success(t("common.success"));
    } catch (error) {
      console.error("Failed to update topic metadata:", error);
      throw error;
    }
  };

  return {
    topics,
    clusters,
    selectedCluster,
    loading,
    setSelectedCluster,
    loadTopics,
    deleteTopic,
    updateMetadata,
  };
}
