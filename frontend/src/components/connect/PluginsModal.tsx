import { useState, useEffect } from "react";
import Button from "../ui/Button";
import Badge from "../ui/Badge";
import Loading from "../ui/Loading";
import { X, Package, CheckCircle } from "lucide-react";

interface Plugin {
  class: string;
  type: string;
  version: string;
}

interface PluginsModalProps {
  isOpen: boolean;
  onClose: () => void;
  connectId: string;
  onSelectPlugin: (pluginClass: string) => void;
}

export default function PluginsModal({
  isOpen,
  onClose,
  connectId,
  onSelectPlugin,
}: PluginsModalProps) {
  const [plugins, setPlugins] = useState<Plugin[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("");
  const [typeFilter, setTypeFilter] = useState("");

  useEffect(() => {
    if (isOpen) {
      loadPlugins();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen]);

  const loadPlugins = async () => {
    try {
      setLoading(true);
      const response = await fetch(`/api/v1/connect/${connectId}/connector-plugins`);
      const data = await response.json();
      setPlugins(data.plugins || []);
    } catch (error) {
      console.error("Failed to load plugins:", error);
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  const filteredPlugins = plugins.filter((plugin) => {
    const matchesSearch = plugin.class.toLowerCase().includes(filter.toLowerCase());
    const matchesType = !typeFilter || plugin.type === typeFilter;
    return matchesSearch && matchesType;
  });

  const types = [...new Set(plugins.map((p) => p.type))];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 overflow-y-auto">
      <div className="w-full max-w-4xl m-4 rounded-lg bg-white shadow-xl">
        <div className="border-b border-gray-200 p-6">
          <div className="flex items-start justify-between">
            <div>
              <div className="flex items-center gap-2">
                <Package className="h-6 w-6 text-blue-600" />
                <h2 className="text-2xl font-bold text-gray-900">Connector Plugins</h2>
              </div>
              <p className="mt-1 text-sm text-gray-600">
                Available connector plugins in this Kafka Connect cluster
              </p>
            </div>
            <button
              onClick={onClose}
              className="rounded-lg p-2 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>

        <div className="p-6 space-y-4">
          {/* Filters */}
          <div className="flex gap-4">
            <div className="flex-1">
              <input
                type="text"
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
                placeholder="Search plugins..."
                className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>
            <div className="w-48">
              <select
                value={typeFilter}
                onChange={(e) => setTypeFilter(e.target.value)}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                <option value="">All Types</option>
                {types.map((type) => (
                  <option key={type} value={type}>
                    {type}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Plugins List */}
          {loading ? (
            <div className="flex justify-center py-12">
              <Loading size="lg" />
            </div>
          ) : (
            <div className="space-y-2 max-h-96 overflow-y-auto">
              {filteredPlugins.length === 0 ? (
                <div className="text-center py-12 text-gray-500">
                  No plugins found matching your criteria
                </div>
              ) : (
                filteredPlugins.map((plugin, idx) => (
                  <div
                    key={idx}
                    className="rounded-lg border border-gray-200 p-4 hover:bg-gray-50 transition-colors"
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <h4 className="font-medium text-gray-900">{plugin.class}</h4>
                          <Badge variant="info">{plugin.type}</Badge>
                        </div>
                        <p className="text-sm text-gray-600">Version: {plugin.version}</p>
                      </div>
                      <div className="flex gap-2">
                        <Button
                          size="sm"
                          variant="secondary"
                          onClick={() => {
                            onSelectPlugin(plugin.class);
                            onClose();
                          }}
                          title="Validate Config"
                        >
                          <CheckCircle className="h-4 w-4" />
                          Validate
                        </Button>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          )}

          {/* Summary */}
          <div className="border-t border-gray-200 pt-4">
            <p className="text-sm text-gray-600">
              Showing {filteredPlugins.length} of {plugins.length} plugins
            </p>
          </div>
        </div>

        <div className="border-t border-gray-200 p-6 bg-gray-50">
          <div className="flex justify-end">
            <Button variant="secondary" onClick={onClose}>
              Close
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
