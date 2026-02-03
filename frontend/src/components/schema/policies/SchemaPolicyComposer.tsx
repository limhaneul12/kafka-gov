import { useState } from "react";
import Button from "../../ui/Button";
import Badge from "../../ui/Badge";
import { X, Save, FileCode, Sparkles } from "lucide-react";
import { GOVERNANCE_PRESETS } from "../../../constants/policyPresets";

interface SchemaPolicyComposerProps {
    isOpen: boolean;
    onClose: () => void;
    onSubmit: (data: any) => Promise<void>;
    initialData?: any;
}

export default function SchemaPolicyComposer({
    isOpen,
    onClose,
    onSubmit,
    initialData,
}: SchemaPolicyComposerProps) {
    const [formData, setFormData] = useState({
        name: initialData?.name || "",
        description: initialData?.description || "",
        policy_type: initialData?.policy_type || "lint",
        target_environment: initialData?.target_environment || "total",
        content: initialData?.content ? JSON.stringify(initialData.content, null, 2) : JSON.stringify(GOVERNANCE_PRESETS[1].content, null, 2),
    });
    const [loading, setLoading] = useState(false);

    if (!isOpen) return null;

    const applyPreset = (presetId: string) => {
        const preset = GOVERNANCE_PRESETS.find(p => p.id === presetId);
        if (preset) {
            setFormData({
                ...formData,
                name: preset.name,
                description: preset.description,
                content: JSON.stringify(preset.content, null, 2),
            });
        }
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            setLoading(true);
            const payload = {
                ...formData,
                content: JSON.parse(formData.content),
                created_by: "admin@example.com",
            };
            await onSubmit(payload);
            onClose();
        } catch (err: any) {
            alert("Invalid JSON format in policy content: " + err.message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="fixed inset-0 z-50 bg-black bg-opacity-50 overflow-y-auto flex items-center justify-center p-4">
            <div className="w-full max-w-3xl max-h-[90vh] flex flex-col rounded-xl bg-white shadow-2xl overflow-hidden">
                <div className="flex items-center justify-between border-b px-6 py-4">
                    <div className="flex items-center gap-2">
                        <FileCode className="h-5 w-5 text-blue-600" />
                        <h2 className="text-lg font-bold text-gray-900">
                            {initialData ? "Update Policy Version" : "Create New Schema Policy"}
                        </h2>
                    </div>
                    <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-lg">
                        <X className="h-5 w-5 text-gray-400" />
                    </button>
                </div>

                <form onSubmit={handleSubmit} className="flex-1 flex flex-col overflow-hidden">
                    <div className="p-6 space-y-5 flex-1 overflow-y-auto custom-scrollbar">
                        {/* Presets Selection */}
                        <div className="bg-blue-50/50 p-4 rounded-xl border border-blue-100 mb-2">
                            <div className="flex items-center gap-2 mb-3 text-blue-700">
                                <Sparkles className="h-4 w-4" />
                                <span className="text-sm font-bold uppercase tracking-wider">Start with a Preset</span>
                            </div>
                            <div className="grid grid-cols-3 gap-3">
                                {GOVERNANCE_PRESETS.map(preset => (
                                    <button
                                        key={preset.id}
                                        type="button"
                                        onClick={() => applyPreset(preset.id)}
                                        className="text-left p-3 bg-white border border-blue-100 rounded-lg hover:border-blue-300 hover:shadow-md transition-all group"
                                    >
                                        <div className="text-xs font-bold text-gray-900 mb-1 group-hover:text-blue-600">{preset.name}</div>
                                        <div className="text-[10px] text-gray-500 line-clamp-2 leading-relaxed">{preset.description}</div>
                                    </button>
                                ))}
                            </div>
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                            <div className="col-span-1">
                                <label className="block text-xs font-bold text-gray-400 uppercase mb-1">Policy Name</label>
                                <input
                                    type="text"
                                    required
                                    value={formData.name}
                                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                                    placeholder="e.g., Default Lint Policy"
                                    className="w-full rounded-lg border-gray-200 focus:border-blue-500 focus:ring-blue-100 transition-all text-sm py-2.5"
                                />
                            </div>
                            <div className="col-span-1">
                                <label className="block text-xs font-bold text-gray-400 uppercase mb-1">Policy Type</label>
                                <select
                                    value={formData.policy_type}
                                    onChange={(e) => setFormData({ ...formData, policy_type: e.target.value })}
                                    className="w-full rounded-lg border-gray-200 text-sm py-2.5"
                                >
                                    <option value="lint">Content Linting</option>
                                    <option value="guardrail">Environment Guardrail</option>
                                </select>
                            </div>
                        </div>

                        <div>
                            <label className="block text-xs font-bold text-gray-400 uppercase mb-1">Target Environment</label>
                            <div className="flex gap-2">
                                {["total", "dev", "stg", "prod"].map((env) => (
                                    <button
                                        key={env}
                                        type="button"
                                        onClick={() => setFormData({ ...formData, target_environment: env })}
                                        className={`flex-1 py-2 px-3 text-xs font-semibold rounded-lg border transition-all ${formData.target_environment === env
                                            ? "bg-blue-600 border-blue-600 text-white shadow-md shadow-blue-200"
                                            : "bg-white border-gray-200 text-gray-500 hover:border-gray-300"
                                            }`}
                                    >
                                        {env.toUpperCase()}
                                    </button>
                                ))}
                            </div>
                        </div>

                        <div>
                            <label className="block text-xs font-bold text-gray-400 uppercase mb-1">Description</label>
                            <textarea
                                value={formData.description}
                                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                                placeholder="Explain the purpose of this policy..."
                                className="w-full rounded-lg border-gray-200 text-sm py-2"
                                rows={2}
                            />
                        </div>

                        <div>
                            <label className="block text-xs font-bold text-gray-400 uppercase mb-1">Policy Content (JSON)</label>
                            <div className="relative group">
                                <textarea
                                    value={formData.content}
                                    onChange={(e) => setFormData({ ...formData, content: e.target.value })}
                                    className="w-full rounded-lg bg-gray-950 border-gray-800 text-blue-300 font-mono text-xs p-4 focus:ring-1 focus:ring-blue-500 outline-none"
                                    rows={8}
                                />
                                <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                    <Badge variant="default" className="bg-gray-800 text-gray-400 border-none text-[10px]">JSON Format Required</Badge>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div className="bg-gray-50 px-6 py-4 flex justify-end gap-3 border-t">
                        <Button variant="secondary" onClick={onClose} type="button">Cancel</Button>
                        <Button type="submit" disabled={loading}>
                            {loading ? (
                                "Saving..."
                            ) : (
                                <>
                                    <Save className="h-4 w-4 mr-2" />
                                    Save Policy
                                </>
                            )}
                        </Button>
                    </div>
                </form>
            </div>
        </div>
    );
}
