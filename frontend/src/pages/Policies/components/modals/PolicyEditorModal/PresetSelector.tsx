import { useTranslation } from "react-i18next";
import { FileCode } from "lucide-react";

interface Preset {
  name: string;
  description: string;
  content: string;
}

interface PresetSelectorProps {
  policyType: string;
  selectedPreset: string;
  presets: Record<string, Preset>;
  onPresetChange: (preset: string) => void;
}

export function PresetSelector({
  policyType,
  selectedPreset,
  presets,
  onPresetChange,
}: PresetSelectorProps) {
  const { t } = useTranslation();

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <FileCode className="h-5 w-5 text-gray-600" />
        <label className="text-sm font-medium text-gray-700">
          Select Preset Template
        </label>
      </div>

      <div className="grid grid-cols-3 gap-3">
        {Object.entries(presets).map(([key, preset]) => (
          <button
            key={key}
            type="button"
            onClick={() => onPresetChange(key)}
            className={`p-4 rounded-lg border-2 text-left transition-all ${
              selectedPreset === key
                ? "border-blue-500 bg-blue-50"
                : "border-gray-200 hover:border-gray-300 bg-white"
            }`}
          >
            <p className="font-semibold text-gray-900 mb-1">{preset.name}</p>
            <p className="text-xs text-gray-600">{preset.description}</p>
          </button>
        ))}
      </div>

      {policyType === "naming" && (
        <div className="text-xs text-gray-500 bg-blue-50 p-3 rounded-lg">
          <p className="font-medium text-blue-900 mb-1">💡 Preset Guidelines:</p>
          <ul className="list-disc list-inside space-y-1 text-blue-800">
            <li><strong>Permissive:</strong> Startups, rapid prototyping</li>
            <li><strong>Balanced:</strong> Mid-size teams with domain structure</li>
            <li><strong>Strict:</strong> Enterprises with PII/compliance needs</li>
          </ul>
        </div>
      )}
    </div>
  );
}
