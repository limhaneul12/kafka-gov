import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/Card";
import Button from "../components/ui/Button";
import Badge from "../components/ui/Badge";
import Loading from "../components/ui/Loading";
import AddConnectionModal from "../components/connection/AddConnectionModal";
import EditConnectionModal from "../components/connection/EditConnectionModal";
import { clustersAPI } from "../services/api";
import { Plus, Server, Database, Edit, Trash2, CheckCircle } from "lucide-react";
import type { KafkaCluster, SchemaRegistry } from "../types";
import { toast } from "sonner";

export default function Connections() {
  const [clusters, setClusters] = useState<KafkaCluster[]>([]);
  const [registries, setRegistries] = useState<SchemaRegistry[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAddModal, setShowAddModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [editType, setEditType] = useState<"kafka" | "registry">("kafka");
  const [editId, setEditId] = useState<string>("");
  const [editData, setEditData] = useState<KafkaCluster | SchemaRegistry | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<{
    isOpen: boolean;
    type: "kafka" | "registry";
    id: string;
    name: string;
  }>({ isOpen: false, type: "kafka", id: "", name: "" });

  // 디버깅: editData와 showEditModal 변경 감지
  useEffect(() => {
    console.log('[Connections] Edit state changed:', {
      showEditModal,
      editType,
      editId,
      hasEditData: !!editData,
    });
  }, [showEditModal, editType, editId, editData]);

  // 디버깅: registries state 변경 감지
  useEffect(() => {
    console.log('[Connections] Registries state updated:', {
      count: registries.length,
      registries: registries.map(r => ({ id: r.registry_id, name: r.name })),
    });
  }, [registries]);

  useEffect(() => {
    loadConnections();
  }, []);

  const loadConnections = async () => {
    try {
      setLoading(true);
      console.log('[Connections] Loading connections...');
      const [clustersRes, registriesRes] = await Promise.all([
        clustersAPI.listKafka(),
        clustersAPI.listRegistries(),
      ]);
      
      console.log('[Connections] API responses:', {
        clusters: clustersRes.data.length,
        registries: registriesRes.data.length,
      });
      console.log('[Connections] Registry list:', registriesRes.data);
      
      setClusters(clustersRes.data);
      setRegistries(registriesRes.data);
      
      console.log('[Connections] State updated successfully');
    } catch (error) {
      console.error("[Connections] Failed to load connections:", error);
      toast.error('연결 목록 로딩 실패', {
        description: error instanceof Error ? error.message : '연결 목록을 불러오는데 실패했습니다.'
      });
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
      }
      await loadConnections();
    } catch (error) {
      console.error("Failed to add connection:", error);
      throw error;
    }
  };

  // Kafka Cluster handlers
  const handleDeleteKafka = (clusterId: string, name: string) => {
    setDeleteConfirm({
      isOpen: true,
      type: "kafka",
      id: clusterId,
      name,
    });
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
  const handleDeleteRegistry = (registryId: string, name: string) => {
    console.log('[Connections] Opening delete confirm for registry:', { registryId, name });
    setDeleteConfirm({
      isOpen: true,
      type: "registry",
      id: registryId,
      name,
    });
  };

  const confirmDelete = async () => {
    const { type, id, name } = deleteConfirm;
    console.log('[Connections] Confirming delete:', { type, id, name });
    
    try {
      switch (type) {
        case "kafka":
          console.log('[Connections] Deleting Kafka cluster:', id);
          await clustersAPI.deleteKafka(id);
          toast.success('삭제 완료', { description: 'Kafka 클러스터가 삭제되었습니다.' });
          break;
        case "registry":
          console.log('[Connections] Deleting Schema Registry:', id);
          await clustersAPI.deleteRegistry(id);
          console.log('[Connections] Schema Registry deleted successfully');
          toast.success('삭제 완료', { description: 'Schema Registry가 삭제되었습니다.' });
          break;
      }
      
      console.log('[Connections] Reloading connections after delete...');
      await loadConnections();
      console.log('[Connections] Connections reloaded');
    } catch (error) {
      console.error('[Connections] Failed to delete:', error);
      toast.error('삭제 실패', { 
        description: error instanceof Error ? error.message : '삭제에 실패했습니다.' 
      });
    } finally {
      console.log('[Connections] Closing delete modal');
      setDeleteConfirm({ isOpen: false, type: "kafka", id: "", name: "" });
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
    console.log('[Connections] Opening edit modal for registry:', registry);
    setEditType("registry");
    setEditId(registry.registry_id);
    setEditData(registry);
    setShowEditModal(true);
    console.log('[Connections] Edit modal state updated:', {
      editType: "registry",
      editId: registry.registry_id,
      showEditModal: true,
    });
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

      {/* Delete Confirmation Modal */}
      {deleteConfirm.isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
          <div className="w-full max-w-md m-4 rounded-lg bg-white shadow-xl p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              삭제 확인
            </h3>
            <p className="text-sm text-gray-600 mb-4">
              정말로 <span className="font-semibold text-red-600">"{deleteConfirm.name}"</span>을(를) 삭제하시겠습니까?
              <br />
              이 작업은 되돌릴 수 없습니다.
            </p>
            <div className="flex justify-end gap-3">
              <Button
                variant="secondary"
                onClick={() => setDeleteConfirm({ isOpen: false, type: "kafka", id: "", name: "" })}
              >
                취소
              </Button>
              <Button
                variant="primary"
                onClick={confirmDelete}
                className="bg-red-600 hover:bg-red-700"
              >
                삭제
              </Button>
            </div>
          </div>
        </div>
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

      {/* Object Storages 섹션은 Object Storage 기능 제거로 삭제되었습니다. */}
    </div>
  );
}
