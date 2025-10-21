import { useTranslation } from "react-i18next";
import { Plus, Upload } from "lucide-react";
import type { TopicMode } from "../../../Topics.types";

interface ModeSelectorProps {
  mode: TopicMode;
  onChange: (mode: TopicMode) => void;
}

export function ModeSelector({ mode, onChange }: ModeSelectorProps) {
  const { t } = useTranslation();

  return (
    <div className="flex gap-2 mb-6">
      <button
        type="button"
        onClick={() => onChange("single")}
        className={`flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-lg border-2 transition-all ${
          mode === "single"
            ? "border-blue-500 bg-blue-50 text-blue-700"
            : "border-gray-200 hover:border-gray-300 text-gray-600"
        }`}
      >
        <Plus className="h-5 w-5" />
        <span className="font-medium">{t("topic.createSingle")}</span>
      </button>
      
      <button
        type="button"
        onClick={() => onChange("batch")}
        className={`flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-lg border-2 transition-all ${
          mode === "batch"
            ? "border-blue-500 bg-blue-50 text-blue-700"
            : "border-gray-200 hover:border-gray-300 text-gray-600"
        }`}
      >
        <Upload className="h-5 w-5" />
        <span className="font-medium">{t("topic.createBatch")}</span>
      </button>
    </div>
  );
}
