import { useState } from "react";
import Button from "../ui/Button";
import { X, CheckCircle, AlertCircle } from "lucide-react";

interface ValidationResult {
  name: string;
  error_count: number;
  groups: string[];
  configs: Array<{
    definition: {
      name: string;
      type: string;
      required: boolean;
      default_value: string;
      importance: string;
      documentation: string;
      group: string;
      order_in_group: number;
      width: string;
      display_name: string;
      dependents: string[];
    };
    value: {
      name: string;
      value: string | null;
      recommended_values: string[];
      errors: string[];
      visible: boolean;
    };
  }>;
}

interface ValidateConfigModalProps {
  isOpen: boolean;
  onClose: () => void;
  connectId: string;
  pluginClass: string;
}

export default function ValidateConfigModal({
  isOpen,
  onClose,
  connectId,
  pluginClass,
}: ValidateConfigModalProps) {
  const [configJson, setConfigJson] = useState("");
  const [result, setResult] = useState<ValidationResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleValidate = async () => {
    try {
      setLoading(true);
      setError(null);
      setResult(null);

      const config = JSON.parse(configJson);

      const response = await fetch(
        `/api/v1/connect/${connectId}/connector-plugins/${encodeURIComponent(pluginClass)}/config/validate`,
        {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(config),
        }
      );

      if (!response.ok) {
        throw new Error(`Validation failed: ${response.statusText}`);
      }

      const data = await response.json();
      setResult(data);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Failed to validate config";
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    setConfigJson("");
    setResult(null);
    setError(null);
    onClose();
  };

  const errorConfigs = result?.configs.filter((c) => c.value.errors.length > 0) || [];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 overflow-y-auto">
      <div className="w-full max-w-4xl m-4 rounded-lg bg-white shadow-xl">
        <div className="border-b border-gray-200 p-6">
          <div className="flex items-start justify-between">
            <div>
              <h2 className="text-2xl font-bold text-gray-900">Validate Connector Config</h2>
              <p className="mt-1 text-sm text-gray-600">{pluginClass}</p>
            </div>
            <button
              onClick={handleClose}
              className="rounded-lg p-2 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>

        <div className="p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Configuration (JSON) *
            </label>
            <textarea
              value={configJson}
              onChange={(e) => setConfigJson(e.target.value)}
              rows={12}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 font-mono text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              placeholder={`{
  "connector.class": "${pluginClass}",
  "tasks.max": "1",
  "topics": "my-topic",
  "key.converter": "org.apache.kafka.connect.json.JsonConverter",
  "value.converter": "org.apache.kafka.connect.json.JsonConverter"
}`}
            />
            <p className="mt-2 text-sm text-gray-500">
              Enter the connector configuration in JSON format
            </p>
          </div>

          {error && (
            <div className="rounded-lg bg-red-50 p-4 flex items-start gap-3">
              <AlertCircle className="h-5 w-5 text-red-600 flex-shrink-0 mt-0.5" />
              <div>
                <h4 className="font-medium text-red-900">Validation Error</h4>
                <p className="mt-1 text-sm text-red-700">{error}</p>
              </div>
            </div>
          )}

          {result && (
            <div className="space-y-4">
              {/* Summary */}
              <div
                className={`rounded-lg p-4 flex items-start gap-3 ${
                  result.error_count === 0
                    ? "bg-green-50"
                    : "bg-yellow-50"
                }`}
              >
                {result.error_count === 0 ? (
                  <>
                    <CheckCircle className="h-5 w-5 text-green-600 flex-shrink-0 mt-0.5" />
                    <div>
                      <h4 className="font-medium text-green-900">Validation Passed</h4>
                      <p className="mt-1 text-sm text-green-700">
                        Configuration is valid ({result.configs.length} configs checked)
                      </p>
                    </div>
                  </>
                ) : (
                  <>
                    <AlertCircle className="h-5 w-5 text-yellow-600 flex-shrink-0 mt-0.5" />
                    <div>
                      <h4 className="font-medium text-yellow-900">Validation Issues Found</h4>
                      <p className="mt-1 text-sm text-yellow-700">
                        {result.error_count} error(s) found in configuration
                      </p>
                    </div>
                  </>
                )}
              </div>

              {/* Errors */}
              {errorConfigs.length > 0 && (
                <div>
                  <h4 className="font-medium text-gray-900 mb-2">Configuration Errors</h4>
                  <div className="space-y-2">
                    {errorConfigs.map((config, idx) => (
                      <div
                        key={idx}
                        className="rounded-lg border border-red-200 bg-red-50 p-3"
                      >
                        <p className="font-medium text-red-900">{config.definition.name}</p>
                        <ul className="mt-1 list-disc list-inside text-sm text-red-700">
                          {config.value.errors.map((err, errIdx) => (
                            <li key={errIdx}>{err}</li>
                          ))}
                        </ul>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* All Configs */}
              <details className="rounded-lg border border-gray-200">
                <summary className="cursor-pointer px-4 py-3 font-medium text-gray-900 hover:bg-gray-50">
                  View All Configuration Fields ({result.configs.length})
                </summary>
                <div className="border-t border-gray-200 p-4 bg-gray-50">
                  <div className="space-y-2 max-h-96 overflow-y-auto">
                    {result.configs.map((config, idx) => (
                      <div
                        key={idx}
                        className="rounded border border-gray-200 bg-white p-3 text-sm"
                      >
                        <div className="flex items-start justify-between">
                          <div>
                            <p className="font-medium text-gray-900">
                              {config.definition.display_name}
                            </p>
                            <p className="text-xs text-gray-500">{config.definition.name}</p>
                          </div>
                          {config.definition.required && (
                            <span className="text-xs text-red-600">Required</span>
                          )}
                        </div>
                        <p className="mt-1 text-gray-600">{config.definition.documentation}</p>
                        {config.value.value !== null && (
                          <p className="mt-1 font-mono text-xs text-blue-600">
                            Value: {config.value.value}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              </details>
            </div>
          )}
        </div>

        <div className="border-t border-gray-200 p-6 bg-gray-50">
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={handleClose}>
              Close
            </Button>
            <Button onClick={handleValidate} disabled={loading || !configJson}>
              {loading ? "Validating..." : "Validate"}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
