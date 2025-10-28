import { useState, useEffect } from "react";
import { Package, CheckCircle, Search } from "lucide-react";
import { Card } from "../../../components/ui/Card";
import Button from "../../../components/ui/Button";
import Badge from "../../../components/ui/Badge";
import Loading from "../../../components/ui/Loading";

interface Plugin {
  class: string;
  type: string;
  version: string;
}

interface PluginsTabProps {
  connectId: string;
  onSelectPlugin: (pluginClass: string) => void;
}

export function PluginsTab({ connectId, onSelectPlugin }: PluginsTabProps) {
  const [plugins, setPlugins] = useState<Plugin[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [typeFilter, setTypeFilter] = useState("");

  useEffect(() => {
    loadPlugins();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [connectId]);

  const loadPlugins = async () => {
    try {
      setLoading(true);
      const response = await fetch(`/api/v1/connect/${connectId}/connector-plugins`);
      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
      const data = await response.json();
      setPlugins(data.plugins || []);
    } catch (error) {
      console.error("Failed to load plugins:", error);
      setPlugins([]);
    } finally {
      setLoading(false);
    }
  };

  const filteredPlugins = plugins.filter((plugin) => {
    const matchesSearch = plugin.class.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesType = !typeFilter || plugin.type === typeFilter;
    return matchesSearch && matchesType;
  });

  const types = [...new Set(plugins.map((p) => p.type))];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Package className="h-8 w-8 text-blue-600" />
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Connector Plugins</h2>
          <p className="text-sm text-gray-600">
            Available connector plugins in this Kafka Connect cluster
          </p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search plugins..."
            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>
        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
          className="px-3 py-2 border border-gray-300 rounded-lg focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        >
          <option value="">All Types</option>
          {types.map((type) => (
            <option key={type} value={type}>
              {type}
            </option>
          ))}
        </select>
      </div>

      {/* Plugins Grid */}
      {loading ? (
        <div className="flex items-center justify-center h-64">
          <Loading size="lg" />
        </div>
      ) : filteredPlugins.length === 0 ? (
        <Card className="p-12 text-center">
          <Package className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <p className="text-gray-500">
            {searchTerm || typeFilter
              ? "No plugins found matching your criteria"
              : "No plugins available"}
          </p>
        </Card>
      ) : (
        <>
          <div className="text-sm text-gray-600 mb-2">
            Showing {filteredPlugins.length} of {plugins.length} plugins
          </div>
          <div className="grid grid-cols-1 gap-4">
            {filteredPlugins.map((plugin, idx) => (
              <Card key={idx} className="p-4 hover:shadow-md transition-shadow">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <Package className="h-5 w-5 text-gray-400" />
                      <h4 className="font-medium text-gray-900 break-all">{plugin.class}</h4>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge variant="info">{plugin.type}</Badge>
                      <span className="text-sm text-gray-600">Version: {plugin.version}</span>
                    </div>
                  </div>
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={() => onSelectPlugin(plugin.class)}
                    title="Use this plugin to create a connector"
                  >
                    <CheckCircle className="h-4 w-4" />
                    Use Plugin
                  </Button>
                </div>
              </Card>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
