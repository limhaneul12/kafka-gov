import { AlertCircle } from "lucide-react";

interface JSONEditorProps {
  value: string;
  onChange: (value: string) => void;
  error?: string;
}

export function JSONEditor({ value, onChange, error }: JSONEditorProps) {

  return (
    <div className="space-y-2">
      <label className="block text-sm font-medium text-gray-700">
        Policy Content (YAML) *
      </label>
      
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className={`w-full h-96 font-mono text-sm rounded-lg border px-4 py-3 focus:outline-none focus:ring-1 ${
          error
            ? "border-red-300 focus:border-red-500 focus:ring-red-500"
            : "border-gray-300 focus:border-blue-500 focus:ring-blue-500"
        }`}
        placeholder="Enter YAML content..."
        spellCheck={false}
        required
      />

      {error && (
        <div className="flex items-start gap-2 p-3 bg-red-50 border border-red-200 rounded-lg">
          <AlertCircle className="h-5 w-5 text-red-600 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="text-sm font-medium text-red-800">YAML Parse Error</p>
            <p className="text-xs text-red-700 mt-1">{error}</p>
          </div>
        </div>
      )}

      <div className="text-xs text-gray-500 space-y-1">
        <p>💡 Tips:</p>
        <ul className="list-disc list-inside space-y-1 ml-2">
          <li>Use YAML format for better readability</li>
          <li>Will be converted to JSON when saved</li>
          <li>Select a preset template above to get started</li>
        </ul>
      </div>
    </div>
  );
}
