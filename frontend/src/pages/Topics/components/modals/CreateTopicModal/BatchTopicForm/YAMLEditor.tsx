import { useTranslation } from "react-i18next";
import { FileCode } from "lucide-react";

interface YAMLEditorProps {
  value: string;
  onChange: (value: string) => void;
}

export function YAMLEditor({ value, onChange }: YAMLEditorProps) {
  const { t } = useTranslation();

  const exampleYAML = `kind: TopicBatch
env: dev
change_id: "2025-01-15_my-project"
items:
  - name: dev.orders.created
    action: create
    config:
      partitions: 3
      replication_factor: 2
      retention_ms: 604800000
      min_insync_replicas: 1
    metadata:
      owner: team-data
      team: data
      doc: "https://wiki.company.com/orders"
      tags: ["orders", "events"]`;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <FileCode className="h-5 w-5 text-gray-600" />
          <label className="text-sm font-medium text-gray-700">
            YAML Content
          </label>
        </div>
        <button
          type="button"
          onClick={() => onChange(exampleYAML)}
          className="text-xs text-blue-600 hover:text-blue-700"
        >
          Load Example
        </button>
      </div>

      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full h-96 font-mono text-sm rounded-lg border border-gray-300 p-4 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        placeholder={exampleYAML}
        spellCheck={false}
      />

      <div className="text-xs text-gray-500 space-y-1">
        <p>💡 Tips:</p>
        <ul className="list-disc list-inside space-y-1 ml-2">
          <li>Use <code className="bg-gray-100 px-1 rounded">---</code> to separate multiple YAML documents</li>
          <li>Supported actions: create, alter, delete</li>
          <li>Environment: dev, stg, prod</li>
        </ul>
      </div>
    </div>
  );
}
