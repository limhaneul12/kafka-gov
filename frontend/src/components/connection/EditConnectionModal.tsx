import { useState, useEffect } from "react";
import Button from "../ui/Button";
import { X } from "lucide-react";

interface EditConnectionModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: Record<string, string>) => Promise<void>;
  type: "kafka" | "registry" | "storage" | "connect";
  initialData: {
    name: string;
    url?: string;
    bootstrap_servers?: string;
    endpoint_url?: string;
    bucket_name?: string;
    description?: string | null;
  };
}

export default function EditConnectionModal({
  isOpen,
  onClose,
  onSubmit,
  type,
  initialData,
}: EditConnectionModalProps) {
  const [formData, setFormData] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (isOpen && initialData) {
      setFormData({
        name: initialData.name || "",
        url: initialData.url || "",
        bootstrap_servers: initialData.bootstrap_servers || "",
        endpoint_url: initialData.endpoint_url || "",
        bucket_name: initialData.bucket_name || "",
        description: initialData.description || "",
      });
    }
  }, [isOpen, initialData]);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    try {
      setLoading(true);
      await onSubmit(formData);
      onClose();
    } catch (error) {
      console.error("Failed to update connection:", error);
      alert("Failed to update connection. Please check your inputs.");
    } finally {
      setLoading(false);
    }
  };

  const renderFields = () => {
    switch (type) {
      case "kafka":
        return (
          <>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Cluster Name *
              </label>
              <input
                type="text"
                value={formData.name || ""}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                required
                className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Bootstrap Servers *
              </label>
              <input
                type="text"
                value={formData.bootstrap_servers || ""}
                onChange={(e) => setFormData({ ...formData, bootstrap_servers: e.target.value })}
                required
                placeholder="kafka:9092"
                className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Description
              </label>
              <textarea
                value={formData.description || ""}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                rows={2}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>
          </>
        );

      case "registry":
        return (
          <>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Registry Name *
              </label>
              <input
                type="text"
                value={formData.name || ""}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                required
                className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                URL *
              </label>
              <input
                type="text"
                value={formData.url || ""}
                onChange={(e) => setFormData({ ...formData, url: e.target.value })}
                required
                placeholder="http://schema-registry:8081"
                className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Description
              </label>
              <textarea
                value={formData.description || ""}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                rows={2}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>
          </>
        );

      case "connect":
        return (
          <>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Connect Name *
              </label>
              <input
                type="text"
                value={formData.name || ""}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                required
                className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                URL *
              </label>
              <input
                type="text"
                value={formData.url || ""}
                onChange={(e) => setFormData({ ...formData, url: e.target.value })}
                required
                placeholder="http://kafka-connect:8083"
                className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
              <p className="mt-1 text-xs text-gray-500">
                Make sure the port is correct (usually 8083)
              </p>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Description
              </label>
              <textarea
                value={formData.description || ""}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                rows={2}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>
          </>
        );

      case "storage":
        return (
          <>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Storage Name *
              </label>
              <input
                type="text"
                value={formData.name || ""}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                required
                className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Endpoint URL *
              </label>
              <input
                type="text"
                value={formData.endpoint_url || ""}
                onChange={(e) => setFormData({ ...formData, endpoint_url: e.target.value })}
                required
                placeholder="http://minio:9000"
                className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Bucket Name *
              </label>
              <input
                type="text"
                value={formData.bucket_name || ""}
                onChange={(e) => setFormData({ ...formData, bucket_name: e.target.value })}
                required
                placeholder="schemas"
                className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Description
              </label>
              <textarea
                value={formData.description || ""}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                rows={2}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>
          </>
        );
    }
  };

  const getTitle = () => {
    switch (type) {
      case "kafka":
        return "Edit Kafka Cluster";
      case "registry":
        return "Edit Schema Registry";
      case "connect":
        return "Edit Kafka Connect";
      case "storage":
        return "Edit Object Storage";
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 overflow-y-auto">
      <div className="w-full max-w-2xl m-4 rounded-lg bg-white shadow-xl">
        <div className="border-b border-gray-200 p-6">
          <div className="flex items-center justify-between">
            <h2 className="text-2xl font-bold text-gray-900">{getTitle()}</h2>
            <button
              onClick={onClose}
              className="rounded-lg p-2 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {renderFields()}

          <div className="flex justify-end gap-3 pt-4">
            <Button type="button" variant="secondary" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" disabled={loading}>
              {loading ? "Saving..." : "Save Changes"}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
