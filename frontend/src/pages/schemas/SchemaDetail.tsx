import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
    BookOpen,
    GitCommit,
    GitPullRequest,
    Trash2,
    Edit3,
    Save,
    X,
    RotateCcw,
    AlertCircle,
    CheckCircle2,
    AlertTriangle
} from 'lucide-react';
import ImpactGraph from '../../components/schema/ImpactGraph';
import { Button } from '../../components/common/Button';
import { Badge } from '../../components/common/Badge';
import { useSchemaDetail } from '../../hooks/schema/useSchemaDetail';
import { toast } from 'sonner';
import { schemasAPI, clustersAPI } from '../../services/api';
import { promptApprovalOverride } from '../../utils/approvalOverride';
import { formatDistanceToNow } from 'date-fns';

// --- Tab Navigation ---

const Tabs = ({
    activeTab,
    onTabChange,
}: {
    activeTab: string;
    onTabChange: (tab: string) => void;
}) => {
    const tabs = [
        { id: 'overview', label: 'Overview' },
        { id: 'history', label: 'History' },
        { id: 'impact', label: 'Impact Analysis' },
    ];

    return (
        <div className="flex border-b border-slate-200 mb-6">
            {tabs.map((tab) => (
                <button
                    key={tab.id}
                    onClick={() => onTabChange(tab.id)}
                    className={`px-6 py-3 text-sm font-medium transition-colors border-b-2 ${activeTab === tab.id
                        ? 'border-blue-600 text-slate-900 font-semibold'
                        : 'border-transparent text-slate-500 hover:text-slate-800 hover:border-slate-300'
                        }`}
                >
                    {tab.label}
                </button>
            ))}
        </div>
    );
};

// --- Overview ---
const OverviewCode = ({ schemaStr }: { schemaStr: string }) => {
    let formattedSchema = schemaStr;
    let isJson = false;
    try {
        if (schemaStr) {
            const parsed = JSON.parse(schemaStr);
            formattedSchema = JSON.stringify(parsed, null, 2);
            isJson = true;
        }
    } catch (e) {
        // Not JSON
    }

    const highlightJSON = (json: string) => {
        if (!json) return json;
        return json
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+-]?\d+)?)/g, (match) => {
                let cls = 'text-[#d2a8ff]'; // number/bool (GitHub Dark numbers)
                if (/^"/.test(match)) {
                    if (/:$/.test(match)) {
                        cls = 'text-[#79c0ff] font-medium'; // key (GitHub Dark keys)
                    } else {
                        cls = 'text-[#a5d6ff]'; // string (GitHub Dark strings)
                    }
                } else if (/true|false/.test(match)) {
                    cls = 'text-[#ff7b72] font-semibold'; // boolean
                } else if (/null/.test(match)) {
                    cls = 'text-slate-500 italic'; // null
                }
                return `<span class="${cls}">${match}</span>`;
            });
    };

    const copyToClipboard = () => {
        navigator.clipboard.writeText(formattedSchema);
        toast.success('Schema copied to clipboard');
    };

    return (
        <div className="relative group">
            <div className="absolute top-4 right-4 z-10 flex gap-2">
                <button
                    onClick={copyToClipboard}
                    className="opacity-0 group-hover:opacity-100 transition-all bg-white/10 hover:bg-white/20 text-white px-3 py-1.5 rounded-md text-xs font-medium backdrop-blur-md border border-white/10"
                >
                    Copy
                </button>
            </div>
            <div className="bg-[#0d1117] rounded-xl p-8 overflow-x-auto shadow-sm border border-[#30363d] ring-1 ring-white/5 min-h-[400px]">
                <pre
                    className="text-sm leading-relaxed font-mono whitespace-pre text-[#c9d1d9]"
                    dangerouslySetInnerHTML={{ __html: isJson ? highlightJSON(formattedSchema) : (formattedSchema || '// No schema found') }}
                />
            </div>
        </div>
    );
};

const JsonDiffHelper = ({ oldStr, newStr }: { oldStr: string | null, newStr: string | null }) => {
    const [diffOnly, setDiffOnly] = useState(true);

    const format = (s: string | null) => {
        try {
            if (!s) return [];
            return JSON.stringify(JSON.parse(s), null, 2).split('\n');
        } catch (e) {
            return s ? s.split('\n') : [];
        }
    };

    const oldLines = format(oldStr);
    const newLines = format(newStr);

    // Calculate line frequencies to avoid highlighting identical lines that just shifted
    const getFreqs = (lines: string[]) => {
        const counts: Record<string, number> = {};
        lines.forEach(l => {
            const t = l.trim();
            counts[t] = (counts[t] || 0) + 1;
        });
        return counts;
    };

    const oldFreqs = getFreqs(oldLines);
    const newFreqs = getFreqs(newLines);

    // Helper to track used line counts during rendering
    const usedOld: Record<string, number> = {};
    const usedNew: Record<string, number> = {};

    const renderLines = (lines: string[], otherFreqs: Record<string, number>, used: Record<string, number>, type: 'added' | 'removed') => {
        return lines.map((line, i) => {
            const trim = line.trim();
            used[trim] = (used[trim] || 0) + 1;

            // A line is changed if it doesn't exist on the other side, 
            // or if we have more occurrences of it on this side than the other side
            const isChanged = !otherFreqs[trim] || used[trim] > otherFreqs[trim];

            if (diffOnly && !isChanged) return null;

            const bgColor = type === 'added' ? 'bg-[#dafbe1] text-[#116329]' : 'bg-[#ffebe9] text-[#a51d2d]';
            const symbol = type === 'added' ? '+' : '-';

            return (
                <div key={i} className={`flex group transition-colors hover:bg-black/[0.02] ${isChanged ? bgColor : 'text-[#24292f]'}`}>
                    <span className="w-10 shrink-0 text-right pr-2 select-none opacity-30 border-r border-[#d0d7de] mr-2 text-[9px] vertical-middle">{i + 1}</span>
                    <span className="w-4 shrink-0 text-center select-none font-bold opacity-60 text-[10px]">{isChanged ? symbol : ' '}</span>
                    <span className="whitespace-pre font-mono text-[11px]">{line}</span>
                </div>
            );
        }).filter(Boolean);
    };

    return (
        <div className="flex flex-col border-t border-[#d0d7de] bg-[#f6f8fa] h-[550px] overflow-hidden">
            <div className="flex items-center justify-between px-4 py-1.5 bg-white border-b border-[#d0d7de]">
                <div className="flex items-center gap-4">
                    <label className="flex items-center gap-2 cursor-pointer group">
                        <input
                            type="checkbox"
                            checked={diffOnly}
                            onChange={e => setDiffOnly(e.target.checked)}
                            className="w-3.5 h-3.5 rounded border-gray-300 text-[#0969da] focus:ring-[#0969da]"
                        />
                        <span className="text-[10px] font-semibold text-[#57606a] group-hover:text-[#24292f]">Hide Unchanged Lines</span>
                    </label>
                </div>
                <span className="text-[9px] font-mono text-[#57606a]">Frequency-based Comparison</span>
            </div>

            <div className="flex flex-1 overflow-hidden">
                <div className="flex-1 flex flex-col border-r border-[#d0d7de] bg-[#fffbfa]">
                    <div className="px-3 py-1.5 bg-white border-b border-[#d0d7de] text-[10px] font-bold text-[#cf222e] uppercase">
                        Original (Current)
                    </div>
                    <div className="flex-1 overflow-auto bg-white/50">
                        {renderLines(oldLines, newFreqs, usedOld, 'removed')}
                        {oldLines.length === 0 && <div className="p-4 text-xs text-[#57606a] italic">No current schema</div>}
                    </div>
                </div>
                <div className="flex-1 flex flex-col bg-[#fafffa]">
                    <div className="px-3 py-1.5 bg-white border-b border-[#d0d7de] text-[10px] font-bold text-[#1a7f37] uppercase">
                        Target (New)
                    </div>
                    <div className="flex-1 overflow-auto bg-white/50">
                        {renderLines(newLines, oldFreqs, usedNew, 'added')}
                        {newLines.length === 0 && <div className="p-4 text-xs text-[#57606a] italic">No target schema</div>}
                    </div>
                </div>
            </div>
        </div>
    );
};

// --- Plan Result View ---
const PlanResultView = ({ item, report, impact, onApply, onCancel }: any) => {
    const [showFullDiff, setShowFullDiff] = useState(false);

    return (
        <div className="animate-in fade-in slide-in-from-bottom-4 duration-300">
            {/* Plan Summary Banner */}
            <div className={`mb-6 p-4 rounded-xl border flex items-center gap-4 ${report.is_compatible
                ? 'bg-[#f0f9ff] border-[#0969da]/20 text-[#0969da]'
                : 'bg-[#fff5f5] border-[#cf222e]/20 text-[#cf222e]'
                }`}>
                <div className={`p-2 rounded-lg ${report.is_compatible ? 'bg-[#0969da]/10' : 'bg-[#cf222e]/10'}`}>
                    {report.is_compatible ? <CheckCircle2 className="w-5 h-5" /> : <AlertTriangle className="w-5 h-5" />}
                </div>
                <div className="flex-1">
                    <div className="flex items-center justify-between mb-0.5">
                        <h4 className="font-bold text-sm">Schema Change Plan</h4>
                        <Badge variant={report.is_compatible ? 'success' : 'error'} className="uppercase text-[10px] tracking-tight">
                            {report.is_compatible ? 'Compatible' : 'Incompatible'}
                        </Badge>
                    </div>
                    <p className="text-xs opacity-80">
                        {report.is_compatible
                            ? `This change is compatible with existing producers and consumers. A new version (v${item.target_version}) will be created.`
                            : `This change violates the ${report.mode} compatibility policy. Applying this may break existing producers or consumers.`
                        }
                    </p>
                </div>
            </div>

            <div className="space-y-4">
                {/* Diff Analysis Section --- */}
                <div className="border border-[#d0d7de] rounded-lg overflow-hidden bg-white shadow-sm">
                    <div className="px-4 py-2 bg-[#f6f8fa] border-b border-[#d0d7de] flex items-center justify-between">
                        <div className="flex items-center gap-2">
                            <GitCommit className="w-4 h-4 text-[#57606a]" />
                            <span className="font-semibold text-[#24292f] text-xs">Structural Changes</span>
                        </div>
                        <div className="flex items-center gap-3">
                            <button
                                onClick={() => setShowFullDiff(!showFullDiff)}
                                className="text-[10px] font-medium text-[#0969da] hover:underline"
                            >
                                {showFullDiff ? 'View Summary' : 'View Code Diff'}
                            </button>
                            <span className="text-[10px] font-mono text-[#57606a] bg-white px-1.5 py-0.5 rounded border border-[#d0d7de]">
                                v{item.current_version || 0} → v{item.target_version}
                            </span>
                        </div>
                    </div>

                    {!showFullDiff ? (
                        <div className="p-4 space-y-2.5">
                            {item.diff.changes.map((change: string, i: number) => (
                                <div key={i} className="flex items-start gap-3 group">
                                    <div className={`mt-1.5 shrink-0 w-2 h-2 rounded-full ${change.toLowerCase().includes('added') ? 'bg-[#1a7f37]' :
                                        change.toLowerCase().includes('removed') ? 'bg-[#cf222e]' :
                                            'bg-[#9a6700]'
                                        }`} />
                                    <span className="text-xs text-[#24292f] font-mono leading-relaxed">{change}</span>
                                </div>
                            ))}
                        </div>
                    ) : (
                        <JsonDiffHelper oldStr={item.current_schema} newStr={item.schema} />
                    )}
                </div>

                {/* Compatibility Details (if failed) --- */}
                {!report.is_compatible && report.issues.length > 0 && (
                    <div className="border border-[#cf222e]/30 rounded-lg overflow-hidden bg-[#fffbfa]">
                        <div className="px-4 py-2 bg-[#ffebe9] border-b border-[#cf222e]/20 flex items-center gap-2">
                            <AlertCircle className="w-4 h-4 text-[#cf222e]" />
                            <span className="font-semibold text-[#cf222e] text-xs">Policy Violations</span>
                        </div>
                        <div className="p-4 space-y-2">
                            {report.issues.map((issue: any, i: number) => (
                                <div key={i} className="text-xs text-[#cf222e] bg-white/50 p-2.5 rounded-md border border-[#cf222e]/10 flex gap-2">
                                    <span className="font-bold shrink-0">[{issue.issue_type || issue.type}]</span>
                                    <span>{issue.message}</span>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* Impact Analysis --- */}
                <div className="border border-[#d0d7de] rounded-lg overflow-hidden bg-white shadow-sm">
                    <div className="px-4 py-2 bg-[#f6f8fa] border-b border-[#d0d7de] flex items-center justify-between">
                        <div className="flex items-center gap-2">
                            <GitPullRequest className="w-4 h-4 text-[#57606a]" />
                            <span className="font-semibold text-[#24292f] text-xs">Distribution Impact</span>
                        </div>
                        {impact.status === 'success' && (
                            <span className="text-[9px] text-[#1a7f37] font-bold uppercase tracking-widest flex items-center gap-1">
                                <CheckCircle2 className="w-3 h-3" /> Analysis Complete
                            </span>
                        )}
                    </div>

                    {impact.status === 'failure' ? (
                        <div className="p-4 bg-[#fff5f5] flex items-center gap-3">
                            <AlertCircle className="w-4 h-4 text-[#cf222e]" />
                            <div className="text-xs text-[#cf222e]">
                                <p className="font-bold">Analysis Failed</p>
                                <p className="opacity-80">{impact.error_message || 'An unexpected error occurred during impact analysis.'}</p>
                            </div>
                        </div>
                    ) : (
                        <div className="p-4 grid grid-cols-2 gap-8">
                            <div>
                                <h5 className="text-[10px] font-bold text-[#57606a] uppercase tracking-wider mb-2">Affected Topics</h5>
                                <div className="flex flex-wrap gap-1.5">
                                    {impact.topics.length > 0 ? impact.topics.map((t: string) => (
                                        <Badge key={t} variant="outline" className="bg-[#fff8eb] border-[#d4a72c]/30 text-[#9a6700] text-[10px] font-mono px-1.5 py-0">{t}</Badge>
                                    )) : <span className="text-[11px] text-[#57606a] italic">No topics found via naming strategy</span>}
                                </div>
                            </div>
                            <div>
                                <h5 className="text-[10px] font-bold text-[#57606a] uppercase tracking-wider mb-2">Connected Consumers</h5>
                                <div className="flex flex-wrap gap-1.5">
                                    {impact.consumers.length > 0 ? impact.consumers.map((c: string) => (
                                        <Badge key={c} variant="outline" className="bg-[#f0fdf4] border-[#1a7f37]/20 text-[#1a7f37] text-[10px] font-mono px-1.5 py-0">{c}</Badge>
                                    )) : <span className="text-[11px] text-[#57606a] italic">No active consumer groups detected</span>}
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            </div>

            <div className="flex justify-end gap-2 pt-4 border-t border-[#d0d7de]">
                <Button variant="ghost" size="sm" onClick={onCancel}>Back to Editor</Button>
                <Button
                    variant="success"
                    size="sm"
                    onClick={onApply}
                    disabled={!report.is_compatible}
                    icon={Save}
                    className="px-6"
                >
                    Apply v{item.target_version}
                </Button>
            </div>
        </div>
    );
};

// --- Main Page ---

export default function SchemaDetail() {
    const { subject } = useParams<{ subject: string }>();
    const navigate = useNavigate();
    const [activeTab, setActiveTab] = useState('overview');
    const [isDeleting, setIsDeleting] = useState(false);
    const [showForceDeleteModal, setShowForceDeleteModal] = useState(false);
    const [deleteWarning, setDeleteWarning] = useState<string>('');

    // Edit & Plan States
    const [isEditing, setIsEditing] = useState(false);
    const [editedSchema, setEditedSchema] = useState('');
    const [compatibility, setCompatibility] = useState('BACKWARD');
    const [planResult, setPlanResult] = useState<any>(null);
    const [isPlanning, setIsPlanning] = useState(false);

    const { detailData, historyData, graphData, loading, reload } = useSchemaDetail(subject, activeTab);

    // Initial value setup for edit
    const startEditing = () => {
        if (detailData) {
            let schema = detailData.schema_str;
            try {
                if (schema) {
                    schema = JSON.stringify(JSON.parse(schema), null, 2);
                }
            } catch (e) {
                // Not JSON, keep as is
            }
            setEditedSchema(schema);
            setCompatibility(detailData.compatibility_mode || 'BACKWARD');
            setIsEditing(true);
            setActiveTab('overview');
        }
    };

    const handlePlan = async () => {
        if (!subject) return;
        try {
            setIsPlanning(true);
            const registriesRes = await clustersAPI.listRegistries();
            const registries = registriesRes.data;
            const activeRegistry = registries?.find((r: any) => r.is_active) || registries?.[0];

            if (!activeRegistry) {
                toast.error('No Active Schema Registry found');
                return;
            }

            const res = await schemasAPI.planChange(activeRegistry.registry_id, {
                subject,
                new_schema: editedSchema,
                compatibility
            });
            setPlanResult(res.data);
            toast.success('Change plan generated');
        } catch (e: any) {
            toast.error(e.response?.data?.detail || 'Planning failed');
        } finally {
            setIsPlanning(false);
        }
    };

    const handleApply = async () => {
        if (!planResult || !subject) return;
        try {
            const registriesRes = await clustersAPI.listRegistries();
            const registries = registriesRes.data;
            const activeRegistry = registries?.find((r: any) => r.is_active) || registries?.[0];

            // Format as batch request (backend expects batch)
            const batchRequest = {
                env: subject.split('.')[0] || 'dev',
                change_id: planResult.change_id,
                approvalOverride: promptApprovalOverride(`schema apply for ${subject}`),
                items: planResult.plan.map((item: any) => ({
                    subject: item.subject,
                    type: item.diff.schema_type,
                    compatibility: planResult.compatibility.find((r: any) => r.subject === item.subject)?.mode,
                    schema: editedSchema,
                }))
            };

            if (!batchRequest.approvalOverride) {
                toast.error('Approval evidence is required for this schema change');
                return;
            }

            await schemasAPI.apply(activeRegistry.registry_id, batchRequest);
            toast.success('Schema successfully updated to next version');
            setIsEditing(false);
            setPlanResult(null);
            reload(); // Refresh data
        } catch (e: any) {
            toast.error(e.response?.data?.detail || 'Apply failed');
        }
    };

    const handleRollback = async (version: number) => {
        if (!subject || !window.confirm(`Rollback to v${version}?`)) return;
        try {
            const registriesRes = await clustersAPI.listRegistries();
            const registries = registriesRes.data;
            const activeRegistry = registries?.find((r: any) => r.is_active) || registries?.[0];

            const res = await schemasAPI.planRollback(activeRegistry.registry_id, {
                subject,
                version
            });
            const plan = res.data;

            // For now, let's just use the planResult flow but specifically for rollback
            setPlanResult(plan);
            // In rollback case, we need the schema from the plan
            // The plan result for rollback contains the old schema content
            let oldSchema = plan.plan[0].schema;
            if (oldSchema) {
                try {
                    oldSchema = JSON.stringify(JSON.parse(oldSchema), null, 2);
                } catch (e) {
                    // Not JSON
                }
                setEditedSchema(oldSchema);
            }

            setActiveTab('overview');
            setIsEditing(true);
        } catch (e: any) {
            toast.error('Rollback plan failed');
        }
    };

    const handleDelete = async () => {
        if (!subject || !window.confirm(`Are you sure you want to delete subject "${subject}"? This will remove all versions.`)) return;

        try {
            setIsDeleting(true);
            const registriesRes = await clustersAPI.listRegistries();
            const registries = registriesRes.data;
            const activeRegistry = registries?.find((r: any) => r.is_active) || registries?.[0];

            if (!activeRegistry) {
                toast.error('No Active Schema Registry found');
                return;
            }

            await schemasAPI.delete(activeRegistry.registry_id, subject);
            toast.success('Subject deleted successfully');
            navigate('/schemas');
        } catch (e: any) {
            const errorMsg = e.response?.data?.detail || 'Delete failed';

            // Check if it's a safety violation that can be forced
            if (e.response?.status === 400 && errorMsg.includes('안전하지 않습니다')) {
                setDeleteWarning(errorMsg);
                setShowForceDeleteModal(true);
            } else {
                console.error('Delete failed', e);
                toast.error(errorMsg);
            }
        } finally {
            setIsDeleting(false);
        }
    };

    const handleConfirmForceDelete = async () => {
        if (!subject) return;

        try {
            setIsDeleting(true);
            const registriesRes = await clustersAPI.listRegistries();
            const registries = registriesRes.data;
            const activeRegistry = registries?.find((r: any) => r.is_active) || registries?.[0];

            if (!activeRegistry) {
                toast.error('No Active Schema Registry found');
                return;
            }

            // Call with force=true
            await schemasAPI.delete(activeRegistry.registry_id, subject, true);
            toast.success('Subject force deleted successfully');
            setShowForceDeleteModal(false);
            navigate('/schemas');
        } catch (e: any) {
            console.error('Force delete failed', e);
            toast.error(e.response?.data?.detail || 'Force delete failed');
        } finally {
            setIsDeleting(false);
        }
    };

    return (
        <div className="min-h-screen bg-[#f6f8fa]">
            {/* Header / Breadcrumbs --- */}
            <div className="bg-white border-b border-[#d0d7de] pt-4 px-8 pb-4">
                <nav className="flex items-center gap-2 text-sm text-[#57606a] mb-4">
                    <span className="hover:text-[#0969da] cursor-pointer" onClick={() => navigate('/schemas')}>Schemas</span>
                    <span className="text-[#d0d7de]">/</span>
                    <div className="flex items-center gap-1.5 font-semibold text-[#24292f]">
                        <BookOpen className="w-4 h-4" />
                        <span>{subject}</span>
                    </div>
                </nav>

                <div className="flex justify-between items-center">
                    <div className="flex items-center gap-3">
                        <div className="p-2 bg-[#f6f8fa] border border-[#d0d7de] rounded-md">
                            <GitPullRequest className="w-5 h-5 text-[#57606a]" />
                        </div>
                        <div>
                            <div className="flex items-center gap-3">
                                <h1 className="text-xl font-bold text-[#24292f]">{subject}</h1>
                                <Badge variant="outline" className="rounded-full text-[10px] font-normal border-[#d0d7de] text-[#57606a]">Public</Badge>
                            </div>
                            {detailData && (
                                <div className="flex gap-4 mt-1 text-xs text-[#57606a]">
                                    <span className="flex items-center gap-1.5">Latest: <span className="font-semibold text-[#24292f]">v{detailData.version}</span></span>
                                    <span className="flex items-center gap-1.5 px-1.5 bg-[#f6f8fa] border border-[#d0d7de] rounded-md font-mono text-[10px]">{detailData.schema_type}</span>
                                    {detailData.owner && <span className="flex items-center gap-1.5">Owner: <span className="font-semibold text-[#24292f]">{detailData.owner}</span></span>}
                                </div>
                            )}
                        </div>
                    </div>

                    <div className="flex gap-2">
                        {!isEditing ? (
                            <>
                                <Button
                                    variant="secondary"
                                    size="sm"
                                    onClick={startEditing}
                                    icon={Edit3}
                                    className="bg-[#f6f8fa] border-[#d0d7de] text-[#24292f] hover:bg-[#f3f4f6]"
                                >
                                    Edit
                                </Button>
                                <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={handleDelete}
                                    icon={Trash2}
                                    className="text-[#cf222e] hover:bg-[#fff5f5] hover:border-[#cf222e]/30 border-none"
                                    disabled={isDeleting}
                                >
                                    {isDeleting ? 'Deleting...' : 'Delete'}
                                </Button>
                            </>
                        ) : (
                            <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => { setIsEditing(false); setPlanResult(null); }}
                                icon={X}
                                className="text-[#57606a] hover:bg-[#f6f8fa]"
                            >
                                Cancel
                            </Button>
                        )}
                    </div>
                </div>

                <div className="mt-6 -mb-4">
                    <Tabs activeTab={activeTab} onTabChange={setActiveTab} />
                </div>
            </div>

            {/* Content Area --- */}
            <div className="px-8 py-6 max-w-[1400px] mx-auto">
                <div className="bg-white rounded-lg border border-[#d0d7de] shadow-sm min-h-[500px]">
                    <div className="p-6">
                        {loading ? (
                            <div className="flex justify-center py-20">
                                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#0969da]" />
                            </div>
                        ) : (
                            <>
                                {activeTab === 'overview' && detailData && (
                                    <div className="space-y-4">
                                        {!isEditing ? (
                                            <>
                                                <div className="flex items-center justify-between">
                                                    <h3 className="text-sm font-semibold text-[#24292f]">Schema Definition</h3>
                                                    <div className="flex items-center gap-2">
                                                        {detailData.policy_score && (
                                                            <div className="flex items-center gap-1.5 mr-2">
                                                                <span className="text-[10px] text-gray-500 uppercase font-bold">Policy Score:</span>
                                                                <span className={`text-xs font-bold ${detailData.policy_score > 0.8 ? 'text-green-600' : 'text-amber-600'}`}>
                                                                    {Math.round(detailData.policy_score * 100)}%
                                                                </span>
                                                            </div>
                                                        )}
                                                        <Badge variant="outline" className="text-[10px] font-mono">v{detailData.version}</Badge>
                                                    </div>
                                                </div>

                                                {/* Violations Sidebar/Section */}
                                                {detailData.violations && detailData.violations.length > 0 && (
                                                    <div className="mt-2 mb-6 p-4 bg-rose-50 border border-rose-100 rounded-xl space-y-3">
                                                        <div className="flex items-center gap-2 text-rose-700">
                                                            <AlertCircle className="w-4 h-4" />
                                                            <h4 className="text-xs font-bold uppercase tracking-wider">Policy Violations ({detailData.violations.length})</h4>
                                                        </div>
                                                        <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                                                            {detailData.violations.map((v: any, i: number) => (
                                                                <div key={i} className="flex items-start gap-2 text-xs bg-white p-2.5 rounded-lg border border-rose-100 shadow-sm">
                                                                    <div className={`mt-0.5 shrink-0 px-1.5 py-0.5 rounded text-[9px] font-bold uppercase ${v.severity === 'critical' || v.severity === 'error' ? 'bg-rose-100 text-rose-600' : 'bg-amber-100 text-amber-600'}`}>
                                                                        {v.severity}
                                                                    </div>
                                                                    <div>
                                                                        <div className="font-bold text-gray-900">{v.rule}</div>
                                                                        <div className="text-gray-500 mt-0.5">{v.message}</div>
                                                                    </div>
                                                                </div>
                                                            ))}
                                                        </div>
                                                    </div>
                                                )}

                                                <OverviewCode schemaStr={detailData.schema_str} />
                                            </>
                                        ) : (
                                            <div className="space-y-6">
                                                {!planResult ? (
                                                    <div className="animate-in fade-in slide-in-from-top-2 duration-300">
                                                        <div className="flex items-center justify-between mb-3">
                                                            <h3 className="text-sm font-semibold text-[#24292f]">Modify Definition</h3>
                                                            <div className="flex items-center gap-2">
                                                                <span className="text-xs text-[#57606a]">Compatibility:</span>
                                                                <select
                                                                    value={compatibility}
                                                                    onChange={(e) => setCompatibility(e.target.value)}
                                                                    className="text-xs border border-[#d0d7de] rounded-md bg-[#f6f8fa] px-2 py-1 outline-none focus:ring-2 focus:ring-[#0969da]/30 transition-all font-semibold text-[#24292f]"
                                                                >
                                                                    {['NONE', 'BACKWARD', 'BACKWARD_TRANSITIVE', 'FORWARD', 'FORWARD_TRANSITIVE', 'FULL', 'FULL_TRANSITIVE'].map(m => (
                                                                        <option key={m} value={m}>{m}</option>
                                                                    ))}
                                                                </select>
                                                            </div>
                                                        </div>
                                                        <textarea
                                                            value={editedSchema}
                                                            onChange={(e) => setEditedSchema(e.target.value)}
                                                            onKeyDown={(e) => {
                                                                if (e.key === 'Tab') {
                                                                    e.preventDefault();
                                                                    const start = e.currentTarget.selectionStart;
                                                                    const end = e.currentTarget.selectionEnd;
                                                                    const value = e.currentTarget.value;
                                                                    const newValue = value.substring(0, start) + "  " + value.substring(end);
                                                                    setEditedSchema(newValue);
                                                                    // Update cursor position in next tick
                                                                    setTimeout(() => {
                                                                        const target = e.target as HTMLTextAreaElement;
                                                                        target.selectionStart = target.selectionEnd = start + 2;
                                                                    }, 0);
                                                                }
                                                            }}
                                                            className="w-full h-[500px] font-mono text-sm p-6 bg-[#0d1117] text-[#c9d1d9] rounded-lg outline-none border border-[#30363d] focus:ring-2 focus:ring-[#0969da]/40 transition-all shadow-xl resize-none leading-relaxed"
                                                            placeholder="Paste or type your schema here..."
                                                            spellCheck={false}
                                                        />
                                                        <div className="flex justify-end gap-2 mt-4">
                                                            <Button variant="secondary" size="sm" onClick={() => setIsEditing(false)}>Cancel</Button>
                                                            <Button
                                                                variant="primary"
                                                                size="sm"
                                                                onClick={handlePlan}
                                                                disabled={isPlanning}
                                                                icon={RotateCcw}
                                                                className="px-6"
                                                            >
                                                                {isPlanning ? 'Analyzing...' : 'Analyze Changes'}
                                                            </Button>
                                                        </div>
                                                    </div>
                                                ) : (
                                                    <PlanResultView
                                                        item={planResult.plan[0]}
                                                        report={planResult.compatibility[0]}
                                                        impact={planResult.impacts[0]}
                                                        onApply={handleApply}
                                                        onCancel={() => setPlanResult(null)}
                                                    />
                                                )}
                                            </div>
                                        )}
                                    </div>
                                )}

                                {activeTab === 'history' && historyData && (
                                    <div className="space-y-4">
                                        <div className="flex items-center justify-between mb-2">
                                            <h3 className="text-sm font-semibold text-[#24292f]">Version Activity</h3>
                                        </div>
                                        <div className="border border-[#d0d7de] rounded-lg overflow-hidden">
                                            {historyData.history.map((item, idx) => (
                                                <div
                                                    key={item.version}
                                                    className={`p-4 flex items-center justify-between hover:bg-[#f6f8fa] transition-colors ${idx !== historyData.history.length - 1 ? 'border-b border-[#d0d7de]' : ''}`}
                                                >
                                                    <div className="flex items-start gap-3">
                                                        <div className="mt-1 p-1.5 bg-[#f6f8fa] border border-[#d0d7de] rounded-md text-[#57606a]">
                                                            <GitCommit className="w-4 h-4" />
                                                        </div>
                                                        <div>
                                                            <div className="flex items-center gap-2 mb-1">
                                                                <span className="text-sm font-bold text-[#24292f]">v{item.version}</span>
                                                                <Badge variant={item.diff_type === 'CREATE' ? 'success' : 'info'} className="text-[10px] px-1.5 py-0 leading-tight">
                                                                    {item.diff_type}
                                                                </Badge>
                                                                <span className="text-[10px] font-mono text-[#57606a] px-1.5 bg-[#f6f8fa] rounded border border-[#d0d7de]">
                                                                    ID: {item.schema_id}
                                                                </span>
                                                            </div>
                                                            <p className="text-xs text-[#57606a] mb-1">
                                                                {item.commit_message || (idx === 0 ? 'Initial schema registration' : 'Schema configuration update')}
                                                            </p>
                                                            <div className="flex items-center gap-2 text-[10px] text-[#8c959f]">
                                                                <span className="font-semibold text-[#57606a]">{item.author || 'system'}</span>
                                                                <span>•</span>
                                                                {item.created_at ? (
                                                                    <span title={new Date(item.created_at).toLocaleString()}>
                                                                        {formatDistanceToNow(new Date(item.created_at), { addSuffix: true })}
                                                                    </span>
                                                                ) : (
                                                                    <span>Time unknown</span>
                                                                )}
                                                            </div>
                                                        </div>
                                                    </div>
                                                    <div className="flex items-center gap-2">
                                                        {idx > 0 && !isEditing && (
                                                            <Button
                                                                variant="outline"
                                                                size="sm"
                                                                onClick={() => handleRollback(item.version)}
                                                                icon={RotateCcw}
                                                                className="h-8 text-[11px] px-3 border-[#d0d7de] text-[#24292f] hover:bg-[#f6f8fa]"
                                                            >
                                                                Restore this version
                                                            </Button>
                                                        )}
                                                        {idx === 0 && (
                                                            <span className="text-[10px] font-bold text-[#1a7f37] bg-[#dafbe1] px-2 py-0.5 rounded-full border border-[#1a7f37]/20 uppercase">Active</span>
                                                        )}
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}

                                {activeTab === 'impact' && graphData && (
                                    <div className="space-y-4">
                                        <div className="flex items-center justify-between">
                                            <h3 className="text-sm font-semibold text-[#24292f]">Dependency Graph</h3>
                                            <div className="flex gap-4 text-[10px] font-medium text-[#57606a]">
                                                <div className="flex items-center gap-1.5">
                                                    <span className="w-2 h-2 rounded-full bg-[#0969da]" /> Schema
                                                </div>
                                                <div className="flex items-center gap-1.5">
                                                    <span className="w-2 h-2 rounded-full bg-[#9a6700]" /> Topic
                                                </div>
                                                <div className="flex items-center gap-1.5">
                                                    <span className="w-2 h-2 rounded-full bg-[#1a7f37]" /> Consumer
                                                </div>
                                            </div>
                                        </div>
                                        <div className="h-[600px] border border-[#d0d7de] rounded-lg overflow-hidden bg-[#f6f8fa]/30">
                                            <ImpactGraph nodes={graphData.nodes} links={graphData.links} />
                                        </div>
                                    </div>
                                )}
                            </>
                        )}
                    </div>
                </div>
            </div>

            {/* Force Delete Confirmation Modal */}
            {showForceDeleteModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
                    <div className="bg-white rounded-xl shadow-xl max-w-lg w-full overflow-hidden border border-rose-200 animate-in fade-in zoom-in-95 duration-200">
                        <div className="p-6">
                            <div className="flex items-start gap-4">
                                <div className="p-3 bg-rose-100 rounded-full shrink-0">
                                    <AlertTriangle className="w-6 h-6 text-rose-600" />
                                </div>
                                <div className="flex-1">
                                    <h3 className="text-lg font-bold text-gray-900 mb-2">Unsafe Delete Warning</h3>
                                    <p className="text-sm text-gray-600 mb-4 whitespace-pre-wrap">
                                        {deleteWarning}
                                    </p>
                                    <div className="bg-rose-50 border border-rose-100 rounded-lg p-3 text-xs text-rose-800 font-medium">
                                        This is a production schema or has dependents. Deleting it may cause system outages.
                                    </div>
                                    <p className="text-sm text-gray-900 font-semibold mt-4">
                                        Do you really want to force delete this schema?
                                    </p>
                                </div>
                            </div>
                        </div>
                        <div className="bg-gray-50 px-6 py-4 flex justify-end gap-3 border-t border-gray-100">
                            <Button
                                variant="ghost"
                                onClick={() => setShowForceDeleteModal(false)}
                                disabled={isDeleting}
                            >
                                Cancel
                            </Button>
                            <Button
                                variant="danger"
                                onClick={handleConfirmForceDelete}
                                className="bg-rose-600 hover:bg-rose-700 text-white"
                                disabled={isDeleting}
                            >
                                {isDeleting ? 'Deleting...' : 'Yes, Force Delete'}
                            </Button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
