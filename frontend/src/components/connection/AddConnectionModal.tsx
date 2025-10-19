import { useState } from "react";
import Button from "../ui/Button";
import { X, Server, Database, HardDrive } from "lucide-react";

interface AddConnectionModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (type: string, data: Record<string, string>) => Promise<void>;
}

type ConnectionType = "kafka" | "registry" | "storage" | "connect";

export default function AddConnectionModal({
  isOpen,
  onClose,
  onSubmit,
}: AddConnectionModalProps) {
  const [connectionType, setConnectionType] = useState<ConnectionType>("kafka");
  const [formData, setFormData] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setLoading(true);
      await onSubmit(connectionType, formData);
      handleClose();
    } catch (error) {
      console.error("Failed to add connection:", error);
      alert("Failed to add connection");
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    setFormData({});
    setConnectionType("kafka");
    onClose();
  };

  const connectionTypes = [
    { value: "kafka", label: "Kafka Cluster", icon: Server },
    { value: "registry", label: "Schema Registry", icon: Database },
    { value: "storage", label: "Object Storage", icon: HardDrive },
    { value: "connect", label: "Kafka Connect", icon: Server },
  ];

  const renderForm = () => {
    switch (connectionType) {
      case "kafka":
        return (
          <>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Cluster ID *
              </label>
              <input
                type="text"
                value={formData.cluster_id || ""}
                onChange={(e) =>
                  setFormData({ ...formData, cluster_id: e.target.value })
                }
                className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                placeholder="local-kafka"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Name *
              </label>
              <input
                type="text"
                value={formData.name || ""}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                placeholder="Local Kafka Cluster"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Bootstrap Servers *
              </label>
              <input
                type="text"
                value={formData.bootstrap_servers || ""}
                onChange={(e) =>
                  setFormData({ ...formData, bootstrap_servers: e.target.value })
                }
                className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                placeholder="localhost:9092"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Security Protocol
              </label>
              <select
                value={formData.security_protocol || "PLAINTEXT"}
                onChange={(e) =>
                  setFormData({ ...formData, security_protocol: e.target.value })
                }
                className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                <option value="PLAINTEXT">PLAINTEXT</option>
                <option value="SSL">SSL</option>
                <option value="SASL_PLAINTEXT">SASL_PLAINTEXT</option>
                <option value="SASL_SSL">SASL_SSL</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Description
              </label>
              <textarea
                value={formData.description || ""}
                onChange={(e) =>
                  setFormData({ ...formData, description: e.target.value })
                }
                className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                rows={3}
                placeholder="Optional description"
              />
            </div>
          </>
        );

      case "registry":
        return (
          <>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Registry ID *
              </label>
              <input
                type="text"
                value={formData.registry_id || ""}
                onChange={(e) =>
                  setFormData({ ...formData, registry_id: e.target.value })
                }
                className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                placeholder="local-registry"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Name *
              </label>
              <input
                type="text"
                value={formData.name || ""}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                placeholder="Local Schema Registry"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                URL *
              </label>
              <input
                type="url"
                value={formData.url || ""}
                onChange={(e) => setFormData({ ...formData, url: e.target.value })}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                placeholder="http://localhost:8081"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Description
              </label>
              <textarea
                value={formData.description || ""}
                onChange={(e) =>
                  setFormData({ ...formData, description: e.target.value })
                }
                className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                rows={3}
                placeholder="Optional description"
              />
            </div>
          </>
        );

      case "storage":
        return (
          <>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Storage ID *
              </label>
              <input
                type="text"
                value={formData.storage_id || ""}
                onChange={(e) =>
                  setFormData({ ...formData, storage_id: e.target.value })
                }
                className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                placeholder="local-minio"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Name *
              </label>
              <input
                type="text"
                value={formData.name || ""}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                placeholder="Local MinIO"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Endpoint URL *
              </label>
              <input
                type="url"
                value={formData.endpoint_url || ""}
                onChange={(e) =>
                  setFormData({ ...formData, endpoint_url: e.target.value })
                }
                className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                placeholder="http://localhost:9000"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Bucket Name *
              </label>
              <input
                type="text"
                value={formData.bucket_name || ""}
                onChange={(e) =>
                  setFormData({ ...formData, bucket_name: e.target.value })
                }
                className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                placeholder="kafka-schemas"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Access Key
              </label>
              <input
                type="text"
                value={formData.access_key || ""}
                onChange={(e) =>
                  setFormData({ ...formData, access_key: e.target.value })
                }
                className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                placeholder="minioadmin"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Secret Key
              </label>
              <input
                type="password"
                value={formData.secret_key || ""}
                onChange={(e) =>
                  setFormData({ ...formData, secret_key: e.target.value })
                }
                className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                placeholder="••••••••"
              />
            </div>
          </>
        );

      case "connect":
        return (
          <>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Connect ID *
              </label>
              <input
                type="text"
                value={formData.connect_id || ""}
                onChange={(e) =>
                  setFormData({ ...formData, connect_id: e.target.value })
                }
                className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                placeholder="local-connect"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Cluster ID *
              </label>
              <input
                type="text"
                value={formData.cluster_id || ""}
                onChange={(e) =>
                  setFormData({ ...formData, cluster_id: e.target.value })
                }
                className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                placeholder="local-kafka"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Name *
              </label>
              <input
                type="text"
                value={formData.name || ""}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                placeholder="Local Kafka Connect"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                URL *
              </label>
              <input
                type="url"
                value={formData.url || ""}
                onChange={(e) => setFormData({ ...formData, url: e.target.value })}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                placeholder="http://localhost:8083"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Description
              </label>
              <textarea
                value={formData.description || ""}
                onChange={(e) =>
                  setFormData({ ...formData, description: e.target.value })
                }
                className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                rows={3}
                placeholder="Optional description"
              />
            </div>
          </>
        );
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black bg-opacity-50 overflow-y-auto">
      <div className="flex min-h-screen items-center justify-center p-4">
        <div className="w-full max-w-2xl rounded-lg bg-white shadow-xl my-8">
        <div className="border-b border-gray-200 p-6">
          <div className="flex items-start justify-between">
            <div>
              <h2 className="text-2xl font-bold text-gray-900">Add Connection</h2>
              <p className="mt-1 text-sm text-gray-600">
                새로운 연결을 추가합니다
              </p>
            </div>
            <button
              onClick={handleClose}
              className="rounded-lg p-2 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col max-h-[calc(90vh-80px)]">
          <div className="p-6 space-y-6 overflow-y-auto flex-1">
            {/* Connection Type Selection */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-3">
                Connection Type *
              </label>
              <div className="grid grid-cols-2 gap-3">
                {connectionTypes.map((type) => {
                  const Icon = type.icon;
                  return (
                    <button
                      key={type.value}
                      type="button"
                      onClick={() => {
                        setConnectionType(type.value as ConnectionType);
                        setFormData({});
                      }}
                      className={`flex items-center gap-3 rounded-lg border-2 p-4 transition-colors ${
                        connectionType === type.value
                          ? "border-blue-500 bg-blue-50"
                          : "border-gray-200 hover:border-gray-300"
                      }`}
                    >
                      <Icon
                        className={`h-5 w-5 ${
                          connectionType === type.value
                            ? "text-blue-600"
                            : "text-gray-400"
                        }`}
                      />
                      <span
                        className={`font-medium ${
                          connectionType === type.value
                            ? "text-blue-900"
                            : "text-gray-700"
                        }`}
                      >
                        {type.label}
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Dynamic Form Fields */}
            {renderForm()}
          </div>

          <div className="border-t border-gray-200 p-6 bg-gray-50 flex-shrink-0">
            <div className="flex justify-end gap-3">
              <Button type="button" variant="secondary" onClick={handleClose}>
                Cancel
              </Button>
              <Button type="submit" disabled={loading}>
                {loading ? "Adding..." : "Add Connection"}
              </Button>
            </div>
          </div>
        </form>
        </div>
      </div>
    </div>
  );
}
