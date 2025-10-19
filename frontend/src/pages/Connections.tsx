import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/Card";
import Button from "../components/ui/Button";
import Badge from "../components/ui/Badge";
import Loading from "../components/ui/Loading";
import AddConnectionModal from "../components/connection/AddConnectionModal";
import { clustersAPI } from "../services/api";
import { Plus, Server, Database, HardDrive, Link } from "lucide-react";
import type { KafkaCluster, SchemaRegistry, ObjectStorage, KafkaConnect } from "../types";

export default function Connections() {
  const [clusters, setClusters] = useState<KafkaCluster[]>([]);
  const [registries, setRegistries] = useState<SchemaRegistry[]>([]);
  const [storages, setStorages] = useState<ObjectStorage[]>([]);
  const [connects, setConnects] = useState<KafkaConnect[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAddModal, setShowAddModal] = useState(false);

  useEffect(() => {
    loadConnections();
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
    } finally {
      setLoading(false);
    }
  };

  const handleAddConnection = async (type: string, data: Record<string, string>) => {
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
    } catch (error) {
      console.error("Failed to add connection:", error);
      throw error;
    }
  };

  if (loading) {
    return (
      <div className="flex h-96 items-center justify-center">
        <Loading size="lg" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Connections</h1>
          <p className="mt-2 text-gray-600">
            Kafka 클러스터 및 관련 리소스 연결을 관리합니다
          </p>
        </div>
        <Button onClick={() => setShowAddModal(true)}>
          <Plus className="h-4 w-4" />
          Add Connection
        </Button>
      </div>

      {/* Add Connection Modal */}
      <AddConnectionModal
        isOpen={showAddModal}
        onClose={() => setShowAddModal(false)}
        onSubmit={handleAddConnection}
      />

      {/* Kafka Clusters */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <Server className="h-5 w-5" />
              Kafka Clusters ({clusters.length})
            </CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {clusters.map((cluster) => (
              <div
                key={cluster.cluster_id}
                className="flex items-center justify-between rounded-lg border border-gray-200 p-4"
              >
                <div>
                  <h4 className="font-medium text-gray-900">{cluster.name}</h4>
                  <p className="text-sm text-gray-600">
                    {cluster.bootstrap_servers}
                  </p>
                </div>
                <Badge variant={cluster.is_active ? "success" : "default"}>
                  {cluster.is_active ? "Active" : "Inactive"}
                </Badge>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Schema Registries */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Database className="h-5 w-5" />
            Schema Registries ({registries.length})
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {registries.map((registry) => (
              <div
                key={registry.registry_id}
                className="flex items-center justify-between rounded-lg border border-gray-200 p-4"
              >
                <div>
                  <h4 className="font-medium text-gray-900">{registry.name}</h4>
                  <p className="text-sm text-gray-600">{registry.url}</p>
                </div>
                <Badge variant={registry.is_active ? "success" : "default"}>
                  {registry.is_active ? "Active" : "Inactive"}
                </Badge>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Kafka Connect */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Link className="h-5 w-5" />
            Kafka Connect ({connects.length})
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {connects.length === 0 ? (
              <p className="text-center text-sm text-gray-500 py-4">
                No Kafka Connect instances found
              </p>
            ) : (
              connects.map((connect) => (
                <div
                  key={connect.connect_id}
                  className="flex items-center justify-between rounded-lg border border-gray-200 p-4"
                >
                  <div>
                    <h4 className="font-medium text-gray-900">{connect.name}</h4>
                    <p className="text-sm text-gray-600">
                      {connect.url}
                    </p>
                    {connect.description && (
                      <p className="text-xs text-gray-500 mt-1">
                        {connect.description}
                      </p>
                    )}
                  </div>
                  <Badge variant={connect.is_active ? "success" : "default"}>
                    {connect.is_active ? "Active" : "Inactive"}
                  </Badge>
                </div>
              ))
            )}
          </div>
        </CardContent>
      </Card>

      {/* Object Storages */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <HardDrive className="h-5 w-5" />
            Object Storages ({storages.length})
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {storages.map((storage) => (
              <div
                key={storage.storage_id}
                className="flex items-center justify-between rounded-lg border border-gray-200 p-4"
              >
                <div>
                  <h4 className="font-medium text-gray-900">{storage.name}</h4>
                  <p className="text-sm text-gray-600">
                    {storage.endpoint_url} / {storage.bucket_name}
                  </p>
                </div>
                <Badge variant={storage.is_active ? "success" : "default"}>
                  {storage.is_active ? "Active" : "Inactive"}
                </Badge>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
