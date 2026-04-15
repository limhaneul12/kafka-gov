import { useState } from "react";
import { Database, X } from "lucide-react";

import Button from "../ui/Button";

interface AddConnectionModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: Record<string, string>) => Promise<void>;
  onUpdate?: (id: string, data: Record<string, unknown>) => Promise<void>;
  editMode?: boolean;
  initialData?: Record<string, unknown>;
}

type ConnectionFormData = Record<string, string>;

export default function AddConnectionModal({
  isOpen,
  onClose,
  onSubmit,
  onUpdate,
  editMode = false,
  initialData,
}: AddConnectionModalProps) {
  const initialFormData: ConnectionFormData = Object.fromEntries(
    Object.entries(initialData ?? {}).map(([key, value]) => [key, typeof value === "string" ? value : value == null ? "" : String(value)]),
  );
  const [formData, setFormData] = useState<ConnectionFormData>(initialFormData);
  const [loading, setLoading] = useState(false);

  if (editMode && initialData && Object.keys(formData).length === 0) {
    setFormData(initialFormData);
  }

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setLoading(true);
      if (editMode && onUpdate) {
        await onUpdate(formData.registry_id || "", formData);
      } else {
        await onSubmit(formData);
      }
      handleClose();
    } catch (error) {
      console.error(`Failed to ${editMode ? "update" : "add"} connection:`, error);
      alert(`Failed to ${editMode ? "update" : "add"} connection`);
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    setFormData({});
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 bg-black bg-opacity-50 overflow-y-auto">
      <div className="flex min-h-screen items-center justify-center p-4">
        <div className="w-full max-w-2xl rounded-lg bg-white shadow-xl my-8">
          <div className="border-b border-gray-200 p-6">
            <div className="flex items-start justify-between">
              <div>
                <h2 className="text-2xl font-bold text-gray-900">
                  {editMode ? "Edit Schema Registry" : "Add Schema Registry"}
                </h2>
                <p className="mt-1 text-sm text-gray-600">Schema lifecycle workflows depend on one active Schema Registry.</p>
              </div>
              <button
                type="button"
                onClick={handleClose}
                className="rounded-lg p-2 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
          </div>

          <form onSubmit={handleSubmit} className="flex flex-col max-h-[calc(90vh-80px)]">
            <div className="p-6 space-y-6 overflow-y-auto flex-1">
              <div>
                <div className="block text-sm font-medium text-gray-700 mb-3">Connection Type</div>
                <div className="flex items-center gap-3 rounded-lg border-2 border-blue-500 bg-blue-50 p-4">
                  <Database className="h-5 w-5 text-blue-600" />
                  <span className="font-medium text-blue-900">Schema Registry</span>
                </div>
              </div>

              <div>
                <label htmlFor="connection-registry-id" className="block text-sm font-medium text-gray-700 mb-2">
                  Registry ID *
                </label>
                <input
                  id="connection-registry-id"
                  type="text"
                  value={formData.registry_id || ""}
                  onChange={(e) => setFormData({ ...formData, registry_id: e.target.value })}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  placeholder="primary-registry"
                  required
                />
              </div>
              <div>
                <label htmlFor="connection-registry-name" className="block text-sm font-medium text-gray-700 mb-2">
                  Name *
                </label>
                <input
                  id="connection-registry-name"
                  type="text"
                  value={formData.name || ""}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  placeholder="Primary Schema Registry"
                  required
                />
              </div>
              <div>
                <label htmlFor="connection-registry-url" className="block text-sm font-medium text-gray-700 mb-2">
                  URL *
                </label>
                <input
                  id="connection-registry-url"
                  type="url"
                  value={formData.url || ""}
                  onChange={(e) => setFormData({ ...formData, url: e.target.value })}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  placeholder="http://localhost:8081"
                  required
                />
              </div>
              <div>
                <label htmlFor="connection-registry-description" className="block text-sm font-medium text-gray-700 mb-2">
                  Description
                </label>
                <textarea
                  id="connection-registry-description"
                  value={formData.description || ""}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  rows={3}
                  placeholder="Optional description"
                />
              </div>
            </div>

            <div className="border-t border-gray-200 p-6 bg-gray-50 flex-shrink-0">
              <div className="flex justify-end gap-3">
                <Button type="button" variant="secondary" onClick={handleClose}>
                  Cancel
                </Button>
                <Button type="submit" disabled={loading}>
                  {loading ? (editMode ? "Updating..." : "Adding...") : editMode ? "Update Registry" : "Add Registry"}
                </Button>
              </div>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
