import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/Card";
import Button from "../components/ui/Button";
import Badge from "../components/ui/Badge";
import Loading from "../components/ui/Loading";
import AddConnectionModal from "../components/connection/AddConnectionModal";
import EditConnectionModal from "../components/connection/EditConnectionModal";
import { clustersAPI } from "../services/api";
import { Plus, Server, Database, HardDrive, Link, Edit, Trash2, CheckCircle } from "lucide-react";
import type { KafkaCluster, SchemaRegistry, ObjectStorage, KafkaConnect } from "../types";
import { toast } from "sonner";

export default function Connections() {
  const [clusters, setClusters] = useState<KafkaCluster[]>([]);
  const [registries, setRegistries] = useState<SchemaRegistry[]>([]);
  const [storages, setStorages] = useState<ObjectStorage[]>([]);
  const [connects, setConnects] = useState<KafkaConnect[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAddModal, setShowAddModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [editType, setEditType] = useState<"kafka" | "registry" | "storage" | "connect">("kafka");
  const [editId, setEditId] = useState<string>("");
  const [editData, setEditData] = useState<KafkaCluster | SchemaRegistry | ObjectStorage | KafkaConnect | null>(null);

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

  // Kafka Cluster handlers
  const handleDeleteKafka = async (clusterId: string, name: string) => {
    if (!confirm(`Delete Kafka Cluster "${name}"? This action cannot be undone.`)) {
      return;
    }
    try {
      await clustersAPI.deleteKafka(clusterId);
      await loadConnections();
      toast.success('삭제 완료', { description: 'Kafka 클러스터가 삭제되었습니다.' });
    } catch (error) {
      console.error("Failed to delete kafka:", error);
      toast.error('삭제 실패', { description: 'Kafka 클러스터 삭제에 실패했습니다.' });
    }
  };

  const handleTestKafka = async (clusterId: string, name: string) => {
    try {
      await clustersAPI.testKafka(clusterId);
      toast.success('연결 테스트 성공', { description: `"${name}" 클러스터 연결이 정상입니다.` });
    } catch (error) {
      console.error("Failed to test kafka:", error);
      toast.error('연결 테스트 실패', { description: `"${name}" 클러스터 연결에 실패했습니다. Bootstrap 서버를 확인하세요.` });
    }
  };

  const handleEditKafka = (cluster: KafkaCluster) => {
    setEditType("kafka");
    setEditId(cluster.cluster_id);
    setEditData(cluster);
    setShowEditModal(true);
  };

  // Schema Registry handlers
  const handleDeleteRegistry = async (registryId: string, name: string) => {
    if (!confirm(`Delete Schema Registry "${name}"? This action cannot be undone.`)) {
      return;
    }
    try {
      await clustersAPI.deleteRegistry(registryId);
      await loadConnections();
      toast.success('삭제 완료', { description: 'Schema Registry가 삭제되었습니다.' });
    } catch (error) {
      console.error("Failed to delete registry:", error);
      toast.error('삭제 실패', { description: 'Schema Registry 삭제에 실패했습니다.' });
    }
  };

  const handleTestRegistry = async (registryId: string, name: string) => {
    try {
      await clustersAPI.testRegistry(registryId);
      toast.success('연결 테스트 성공', { description: `"${name}" 레지스트리 연결이 정상입니다.` });
    } catch (error) {
      console.error("Failed to test registry:", error);
      toast.error('연결 테스트 실패', { description: `"${name}" 레지스트리 연결에 실패했습니다. URL을 확인하세요.` });
    }
  };

  const handleEditRegistry = (registry: SchemaRegistry) => {
    setEditType("registry");
    setEditId(registry.registry_id);
    setEditData(registry);
    setShowEditModal(true);
  };

  // Object Storage handlers
  const handleDeleteStorage = async (storageId: string, name: string) => {
    if (!confirm(`Delete Object Storage "${name}"? This action cannot be undone.`)) {
      return;
    }
    try {
      await clustersAPI.deleteStorage(storageId);
      await loadConnections();
      toast.success('삭제 완료', { description: 'Object Storage가 삭제되었습니다.' });
    } catch (error) {
      console.error("Failed to delete storage:", error);
      toast.error('삭제 실패', { description: 'Object Storage 삭제에 실패했습니다.' });
    }
  };

  const handleTestStorage = async (storageId: string, name: string) => {
    try {
      await clustersAPI.testStorage(storageId);
      toast.success('연결 테스트 성공', { description: `"${name}" 스토리지 연결이 정상입니다.` });
    } catch (error) {
      console.error("Failed to test storage:", error);
      toast.error('연결 테스트 실패', { description: `"${name}" 스토리지 연결에 실패했습니다. Endpoint URL을 확인하세요.` });
    }
  };

  const handleEditStorage = (storage: ObjectStorage) => {
    setEditType("storage");
    setEditId(storage.storage_id);
    setEditData(storage);
    setShowEditModal(true);
  };

  // Kafka Connect handlers
  const handleDeleteConnect = async (connectId: string, name: string) => {
    if (!confirm(`Delete Kafka Connect "${name}"? This action cannot be undone.`)) {
      return;
    }
    try {
      await clustersAPI.deleteConnect(connectId);
      await loadConnections();
      toast.success('삭제 완룼', { description: 'Kafka Connect가 삭제되었습니다.' });
    } catch (error) {
      console.error("Failed to delete connect:", error);
      toast.error('삭제 실패', { description: 'Kafka Connect 삭제에 실패했습니다.' });
    }
  };

  const handleTestConnect = async (connectId: string, name: string) => {
    try {
      await clustersAPI.testConnect(connectId);
      toast.success('연결 테스트 성공', { description: `"${name}" Kafka Connect 연결이 정상입니다.` });
    } catch (error) {
      console.error("Failed to test connect:", error);
      toast.error('연결 테스트 실패', { description: `"${name}" Kafka Connect 연결에 실패했습니다. URL을 확인하세요.` });
    }
  };

  const handleEditConnect = (connect: KafkaConnect) => {
    setEditType("connect");
    setEditId(connect.connect_id);
    setEditData(connect);
    setShowEditModal(true);
  };

  const handleUpdateConnection = async (data: Record<string, string>) => {
    try {
      switch (editType) {
        case "kafka":
          await clustersAPI.updateKafka(editId, data);
          break;
        case "registry":
          await clustersAPI.updateRegistry(editId, data);
          break;
        case "storage":
          await clustersAPI.updateStorage(editId, data);
          break;
        case "connect":
          await clustersAPI.updateConnect(editId, data);
          break;
      }
      await loadConnections();
      toast.success('수정 완료', { description: '연결 설정이 업데이트되었습니다.' });
    } catch (error) {
      console.error("Failed to update connection:", error);
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

      {/* Edit Connection Modal */}
      {editData && (
        <EditConnectionModal
          isOpen={showEditModal}
          onClose={() => {
            setShowEditModal(false);
            setEditData(null);
          }}
          onSubmit={handleUpdateConnection}
          type={editType}
          initialData={editData}
        />
      )}

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
                <div className="flex-1">
                  <h4 className="font-medium text-gray-900">{cluster.name}</h4>
                  <p className="text-sm text-gray-600">
                    {cluster.bootstrap_servers}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant={cluster.is_active ? "success" : "default"}>
                    {cluster.is_active ? "Active" : "Inactive"}
                  </Badge>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => handleTestKafka(cluster.cluster_id, cluster.name)}
                    title="Test Connection"
                  >
                    <CheckCircle className="h-4 w-4 text-blue-600" />
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => handleEditKafka(cluster)}
                    title="Edit"
                  >
                    <Edit className="h-4 w-4 text-gray-600" />
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => handleDeleteKafka(cluster.cluster_id, cluster.name)}
                    title="Delete"
                  >
                    <Trash2 className="h-4 w-4 text-red-600" />
                  </Button>
                </div>
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
                <div className="flex-1">
                  <h4 className="font-medium text-gray-900">{registry.name}</h4>
                  <p className="text-sm text-gray-600">{registry.url}</p>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant={registry.is_active ? "success" : "default"}>
                    {registry.is_active ? "Active" : "Inactive"}
                  </Badge>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => handleTestRegistry(registry.registry_id, registry.name)}
                    title="Test Connection"
                  >
                    <CheckCircle className="h-4 w-4 text-blue-600" />
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => handleEditRegistry(registry)}
                    title="Edit"
                  >
                    <Edit className="h-4 w-4 text-gray-600" />
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => handleDeleteRegistry(registry.registry_id, registry.name)}
                    title="Delete"
                  >
                    <Trash2 className="h-4 w-4 text-red-600" />
                  </Button>
                </div>
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
                  <div className="flex-1">
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
                  <div className="flex items-center gap-2">
                    <Badge variant={connect.is_active ? "success" : "default"}>
                      {connect.is_active ? "Active" : "Inactive"}
                    </Badge>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => handleTestConnect(connect.connect_id, connect.name)}
                      title="Test Connection"
                    >
                      <CheckCircle className="h-4 w-4 text-blue-600" />
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => handleEditConnect(connect)}
                      title="Edit"
                    >
                      <Edit className="h-4 w-4 text-gray-600" />
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => handleDeleteConnect(connect.connect_id, connect.name)}
                      title="Delete"
                    >
                      <Trash2 className="h-4 w-4 text-red-600" />
                    </Button>
                  </div>
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
                <div className="flex-1">
                  <h4 className="font-medium text-gray-900">{storage.name}</h4>
                  <p className="text-sm text-gray-600">
                    {storage.endpoint_url} / {storage.bucket_name}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant={storage.is_active ? "success" : "default"}>
                    {storage.is_active ? "Active" : "Inactive"}
                  </Badge>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => handleTestStorage(storage.storage_id, storage.name)}
                    title="Test Connection"
                  >
                    <CheckCircle className="h-4 w-4 text-blue-600" />
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => handleEditStorage(storage)}
                    title="Edit"
                  >
                    <Edit className="h-4 w-4 text-gray-600" />
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => handleDeleteStorage(storage.storage_id, storage.name)}
                    title="Delete"
                  >
                    <Trash2 className="h-4 w-4 text-red-600" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
