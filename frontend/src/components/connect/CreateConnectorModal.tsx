import { useState } from "react";
import Button from "../ui/Button";
import { X } from "lucide-react";

interface ConnectorConfig {
  name: string;
  config: Record<string, string | number>;
}

interface CreateConnectorModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (config: ConnectorConfig) => Promise<void>;
  connectId: string;
}

export default function CreateConnectorModal({
  isOpen,
  onClose,
  onSubmit,
}: CreateConnectorModalProps) {
  const [connectorName, setConnectorName] = useState("");
  const [connectorClass, setConnectorClass] = useState("");
  const [tasksMax, setTasksMax] = useState("1");
  const [customConfig, setCustomConfig] = useState("");
  const [loading, setLoading] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    try {
      setLoading(true);

      // Parse custom config
      let parsedConfig: Record<string, string | number> = {};
      if (customConfig.trim()) {
        try {
          parsedConfig = JSON.parse(customConfig);
        } catch {
          alert("Invalid JSON in custom config");
          return;
        }
      }

      const config = {
        name: connectorName,
        config: {
          "connector.class": connectorClass,
          "tasks.max": tasksMax,
          ...parsedConfig,
        },
      };

      await onSubmit(config);
      handleClose();
    } catch (error) {
      console.error("Failed to create connector:", error);
      const errorMessage = error instanceof Error ? error.message : "Failed to create connector";
      alert(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    setConnectorName("");
    setConnectorClass("");
    setTasksMax("1");
    setCustomConfig("");
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className="w-full max-w-2xl rounded-lg bg-white p-6 shadow-xl">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-2xl font-bold text-gray-900">Create Connector</h2>
          <button
            onClick={handleClose}
            className="rounded-lg p-2 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Connector Name *
            </label>
            <input
              type="text"
              value={connectorName}
              onChange={(e) => setConnectorName(e.target.value)}
              required
              className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              placeholder="my-connector"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Connector Class *
            </label>
            <input
              type="text"
              value={connectorClass}
              onChange={(e) => setConnectorClass(e.target.value)}
              required
              className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              placeholder="org.apache.kafka.connect.file.FileStreamSourceConnector"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Tasks Max
            </label>
            <input
              type="number"
              value={tasksMax}
              onChange={(e) => setTasksMax(e.target.value)}
              min="1"
              className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Custom Configuration (JSON)
            </label>
            <textarea
              value={customConfig}
              onChange={(e) => setCustomConfig(e.target.value)}
              rows={10}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 font-mono text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              placeholder={`{
  "topic": "my-topic",
  "file": "/tmp/test.txt",
  "key.converter": "org.apache.kafka.connect.json.JsonConverter"
}`}
            />
            <p className="mt-1 text-sm text-gray-500">
              Additional configuration properties in JSON format
            </p>
          </div>

          <div className="flex justify-end gap-2 pt-4">
            <Button type="button" variant="secondary" onClick={handleClose}>
              Cancel
            </Button>
            <Button type="submit" disabled={loading}>
              {loading ? "Creating..." : "Create Connector"}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
