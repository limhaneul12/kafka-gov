import { X, History, User, Clock, ShieldCheck, FileCode } from "lucide-react";
import Button from "../../ui/Button";
import Badge from "../../ui/Badge";
import type { SchemaPolicyRecord, SchemaPolicyRule } from "../../../types/schemaPolicy";

interface SchemaPolicyDetailModalProps {
    isOpen: boolean;
    onClose: () => void;
    policy: SchemaPolicyRecord | null;
    history: SchemaPolicyRecord[];
    onActivateVersion: (version: number) => void;
}

export default function SchemaPolicyDetailModal({
    isOpen,
    onClose,
    policy,
    history,
    onActivateVersion,
}: SchemaPolicyDetailModalProps) {
    if (!isOpen || !policy) return null;

    return (
        <div className="fixed inset-0 z-50 bg-black bg-opacity-50 overflow-y-auto flex items-center justify-center p-4">
            <div className="w-full max-w-4xl max-h-[90vh] flex flex-col rounded-xl bg-white shadow-2xl overflow-hidden animate-in fade-in zoom-in duration-200">
                {/* Header */}
                <div className="flex items-center justify-between border-b px-6 py-4">
                    <div className="flex items-center gap-3">
                        <div className="p-2 bg-blue-50 text-blue-600 rounded-lg">
                            <ShieldCheck className="h-6 w-6" />
                        </div>
                        <div>
                            <h2 className="text-xl font-bold text-gray-900">{policy.name}</h2>
                            <p className="text-sm text-gray-500">ID: {policy.policy_id}</p>
                        </div>
                    </div>
                    <button type="button" onClick={onClose} className="p-2 hover:bg-gray-100 rounded-full">
                        <X className="h-6 w-6 text-gray-400" />
                    </button>
                </div>

                <div className="p-6 grid grid-cols-1 lg:grid-cols-3 gap-6 overflow-y-auto flex-1 custom-scrollbar">
                    {/* Main Content */}
                    <div className="lg:col-span-2 space-y-6">
                        <section>
                            <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-2">Description</h3>
                            <p className="text-gray-700 leading-relaxed">{policy.description}</p>
                        </section>

                        <section>
                            <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-2 flex items-center gap-2">
                                <FileCode className="h-4 w-4" />
                                Policy Configuration
                            </h3>
                            <div className="space-y-4">
                                {/* Rule sets */}
                                {policy.content?.rules && (
                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                        {Object.entries(policy.content.rules).map(([ruleName, rule]) => {
                                            const typedRule = rule as SchemaPolicyRule;
                                            return typedRule.enabled && (
                                                <div key={ruleName} className="p-3 bg-white border border-gray-100 rounded-xl shadow-sm flex items-center justify-between">
                                                    <div className="flex flex-col">
                                                        <span className="text-xs font-bold text-gray-900">{ruleName}</span>
                                                        <span className="text-[10px] text-gray-400">Severity: {typedRule.severity || 'warning'}</span>
                                                    </div>
                                                    <Badge
                                                        variant={typedRule.severity === 'error' || typedRule.severity === 'critical' ? 'danger' : 'warning'}
                                                        className="text-[9px] uppercase"
                                                    >
                                                        {typedRule.severity || 'warning'}
                                                    </Badge>
                                                </div>
                                            );
                                        })}
                                    </div>
                                )}

                                {/* Guardrails */}
                                {policy.content?.guardrails && (
                                    <div className="p-4 bg-blue-50/50 rounded-xl border border-blue-100/50">
                                        <h4 className="text-[10px] font-bold text-blue-600 uppercase mb-2">Environment Guardrails</h4>
                                        <div className="space-y-2">
                                            {policy.content.guardrails.allowed_compatibility && (
                                                <div className="text-xs flex items-center gap-2">
                                                    <span className="text-gray-500">Allowed Compatibility:</span>
                                                    <div className="flex flex-wrap gap-1">
                                                        {policy.content.guardrails.allowed_compatibility.map((c: string) => (
                                                            <span key={c} className="px-1.5 py-0.5 bg-blue-100 text-blue-700 rounded text-[10px] font-bold">{c}</span>
                                                        ))}
                                                    </div>
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                )}

                                <div className="bg-gray-950 rounded-lg p-2 font-mono text-[10px] text-blue-300 opacity-50 hover:opacity-100 transition-opacity">
                                    <p className="text-[9px] text-gray-600 mb-1 font-sans italic">Raw Configuration Source</p>
                                    <pre className="max-h-40 overflow-auto custom-scrollbar">{JSON.stringify(policy.content, null, 2)}</pre>
                                </div>
                            </div>
                        </section>

                        <section className="bg-gray-50 rounded-xl p-4 grid grid-cols-2 md:grid-cols-4 gap-4">
                            <div className="space-y-1">
                                <div className="text-[10px] text-gray-400 font-bold uppercase">Target Env</div>
                                <div className="text-sm font-semibold capitalize bg-white border rounded px-2 py-1 inline-block">{policy.target_environment}</div>
                            </div>
                            <div className="space-y-1">
                                <div className="text-[10px] text-gray-400 font-bold uppercase">Type</div>
                                <div><Badge variant="info" className="capitalize">{policy.policy_type}</Badge></div>
                            </div>
                            <div className="space-y-1">
                                <div className="text-[10px] text-gray-400 font-bold uppercase">Current Version</div>
                                <div className="text-sm font-bold text-blue-600">v{policy.version}</div>
                            </div>
                            <div className="space-y-1">
                                <div className="text-[10px] text-gray-400 font-bold uppercase">Status</div>
                                <div><Badge variant={policy.status === "active" ? "success" : "info"} className="capitalize">{policy.status}</Badge></div>
                            </div>
                        </section>
                    </div>

                    {/* History Sidebar */}
                    <div className="lg:col-span-1 border-l pl-6">
                        <h3 className="flex items-center gap-2 text-sm font-bold text-gray-900 mb-4">
                            <History className="h-4 w-4" />
                            Version History
                        </h3>
                        <div className="space-y-4 max-h-[500px] overflow-y-auto pr-2 custom-scrollbar">
                            {history.map((item) => (
                                <div
                                    key={item.version}
                                    className={`p-3 rounded-lg border transition-all ${item.version === policy.version ? 'bg-blue-50 border-blue-200 ring-1 ring-blue-100' : 'bg-white hover:border-gray-300'}`}
                                >
                                    <div className="flex justify-between items-start mb-2">
                                        <span className="text-sm font-bold text-gray-900 font-mono">v{item.version}</span>
                                        <Badge variant={item.status === "active" ? "success" : "default"}>{item.status}</Badge>
                                    </div>
                                    <div className="space-y-2">
                                        <div className="flex items-center gap-2 text-[10px] text-gray-500">
                                            <User className="h-3 w-3" />
                                            {item.created_by}
                                        </div>
                                        <div className="flex items-center gap-2 text-[10px] text-gray-500">
                                            <Clock className="h-3 w-3" />
                                            {new Date(item.created_at).toLocaleString()}
                                        </div>
                                    </div>
                                    {item.status !== "active" && (
                                        <Button
                                            variant="ghost"
                                            size="sm"
                                            className="w-full mt-3 text-xs bg-gray-50 border border-transparent hover:border-gray-200"
                                            onClick={() => onActivateVersion(item.version)}
                                        >
                                            Rollback to v{item.version}
                                        </Button>
                                    )}
                                </div>
                            ))}
                        </div>
                    </div>
                </div>

                {/* Footer */}
                <div className="bg-gray-50 border-t px-6 py-4 flex justify-end">
                    <Button variant="secondary" onClick={onClose}>Close Detail</Button>
                </div>
            </div>
        </div>
    );
}
