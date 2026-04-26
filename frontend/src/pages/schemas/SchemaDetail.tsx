import { useMemo, useState } from 'react';
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
import { Button } from '../../components/common/Button';
import { Badge } from '../../components/common/Badge';
import { useSchemaDetail } from '../../hooks/schema/useSchemaDetail';
import { toast } from 'sonner';
import { schemasAPI } from '../../services/api';
import type {
    SchemaDriftResponse,
    SchemaHistoryResponse,
    SchemaVersionCompareResponse,
    SchemaVersionDetailResponse,
} from '../../types/schema';
import { promptApprovalOverride } from '../../utils/approvalOverride';
import { downloadText } from '../../utils/download';
import { extractErrorStatus } from '../../utils/error';
import { formatDistanceToNow } from 'date-fns';
import {
    describeGovernanceError,
    requireActiveRegistry,
} from '../../utils/schemaGovernance';
import { confirmSchemaGovernanceAction } from '../../utils/schemaGovernancePrompts';

interface SubjectViolation {
    rule: string;
    message: string;
    severity: string;
}

interface SubjectDetailData {
    subject: string;
    version: number;
    schema_id: number;
    schema_str: string;
    schema_type: string;
    compatibility_mode: string;
    owner: string | null;
    doc?: string | null;
    tags?: string[];
    description?: string | null;
    updated_at: string;
    violations: SubjectViolation[];
    policy_score: number;
}

interface SchemaPlanDiff {
    schema_type: string;
    changes: string[];
}

interface SchemaPlanItem {
    subject: string;
    current_version: number | null;
    target_version: number | null;
    diff: SchemaPlanDiff;
    current_schema: string | null;
    schema: string | null;
    schema_definition?: string | null;
}

interface SchemaCompatibilityIssue {
    issue_type?: string;
    type?: string;
    message: string;
}

interface SchemaCompatibilityReport {
    subject: string;
    mode: string;
    is_compatible: boolean;
    issues: SchemaCompatibilityIssue[];
}

interface SchemaImpactRecord {
    status: string;
    error_message?: string | null;
}

interface SchemaPlanResult {
    change_id: string;
    plan: SchemaPlanItem[];
    compatibility: SchemaCompatibilityReport[];
    impacts: SchemaImpactRecord[];
}

interface SchemaApplyItemRequest {
    subject: string;
    type: string;
    compatibility: string | undefined;
    schema: string;
}

interface SchemaBatchApplyRequest {
    env: string;
    change_id: string;
    approvalOverride: ReturnType<typeof promptApprovalOverride>;
    items: SchemaApplyItemRequest[];
}

interface RollbackExecutePayload {
    subject: string;
    version: number;
    reason?: string;
    approvalOverride: ReturnType<typeof promptApprovalOverride>;
}

interface SchemaSettingsPayload {
    owner?: string | null;
    doc?: string | null;
    tags?: string[];
    description?: string | null;
    compatibilityMode?: string | null;
}

const extractDownloadFilename = (
    headers: Record<string, string | undefined> | undefined,
    fallback: string,
): string => {
    const disposition = headers?.['content-disposition'] || headers?.['Content-Disposition'];
    if (!disposition) {
        return fallback;
    }
    const match = disposition.match(/filename="?([^";]+)"?/i);
    return match?.[1] || fallback;
};

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
    ];

    return (
        <div className="flex border-b border-slate-200 mb-6">
            {tabs.map((tab) => (
                <button
                    type="button"
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
    try {
        if (schemaStr) {
            const parsed = JSON.parse(schemaStr);
            formattedSchema = JSON.stringify(parsed, null, 2);
        }
    } catch {
        // Not JSON
    }

    const copyToClipboard = () => {
        navigator.clipboard.writeText(formattedSchema);
        toast.success('Schema copied to clipboard');
    };

    return (
        <div className="relative group">
            <div className="absolute top-4 right-4 z-10 flex gap-2">
                <button
                    type="button"
                    onClick={copyToClipboard}
                    className="opacity-0 group-hover:opacity-100 transition-all bg-white/10 hover:bg-white/20 text-white px-3 py-1.5 rounded-md text-xs font-medium backdrop-blur-md border border-white/10"
                >
                    Copy
                </button>
            </div>
            <div className="bg-[#0d1117] rounded-xl p-8 overflow-x-auto shadow-sm border border-[#30363d] ring-1 ring-white/5 min-h-[400px]">
                <pre className="text-sm leading-relaxed font-mono whitespace-pre text-[#c9d1d9]">
                    <code>{formattedSchema || '// No schema found'}</code>
                </pre>
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
        } catch {
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
        const keyCounts: Record<string, number> = {};

        return lines.map((line, i) => {
            const trim = line.trim();
            used[trim] = (used[trim] || 0) + 1;
            keyCounts[trim] = (keyCounts[trim] || 0) + 1;

            // A line is changed if it doesn't exist on the other side, 
            // or if we have more occurrences of it on this side than the other side
            const isChanged = !otherFreqs[trim] || used[trim] > otherFreqs[trim];

            if (diffOnly && !isChanged) return null;

            const bgColor = type === 'added' ? 'bg-[#dafbe1] text-[#116329]' : 'bg-[#ffebe9] text-[#a51d2d]';
            const symbol = type === 'added' ? '+' : '-';
            const lineKey = `${type}-${trim || 'empty'}-${keyCounts[trim]}`;

            return (
                <div key={lineKey} className={`flex group transition-colors hover:bg-black/[0.02] ${isChanged ? bgColor : 'text-[#24292f]'}`}>
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
const PlanResultView = ({
    item,
    report,
    onApply,
    onCancel,
}: {
    item: SchemaPlanItem;
    report: SchemaCompatibilityReport;
    onApply: () => Promise<void>;
    onCancel: () => void;
}) => {
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
                                type="button"
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
                            {item.diff.changes.map((change: string) => (
                                <div key={change} className="flex items-start gap-3 group">
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
                            {report.issues.map((issue) => (
                                <div key={`${issue.issue_type || issue.type}-${issue.message}`} className="text-xs text-[#cf222e] bg-white/50 p-2.5 rounded-md border border-[#cf222e]/10 flex gap-2">
                                    <span className="font-bold shrink-0">[{issue.issue_type || issue.type}]</span>
                                    <span>{issue.message}</span>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

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
    const [compatibility, setCompatibility] = useState('');
    const [planResult, setPlanResult] = useState<SchemaPlanResult | null>(null);
    const [isPlanning, setIsPlanning] = useState(false);
    const [versionPreview, setVersionPreview] = useState<SchemaVersionDetailResponse | null>(null);
    const [isPreviewLoading, setIsPreviewLoading] = useState(false);
    const [versionComparison, setVersionComparison] = useState<SchemaVersionCompareResponse | null>(null);
    const [isComparisonLoading, setIsComparisonLoading] = useState(false);
    const [rollbackTargetVersion, setRollbackTargetVersion] = useState<number | null>(null);
    const [isEditingSettings, setIsEditingSettings] = useState(false);
    const [settingsOwner, setSettingsOwner] = useState('');
    const [settingsDoc, setSettingsDoc] = useState('');
    const [settingsDescription, setSettingsDescription] = useState('');
    const [settingsTags, setSettingsTags] = useState('');
    const [settingsCompatibility, setSettingsCompatibility] = useState('');

    const { detailData, historyData, driftData, loading, reload } = useSchemaDetail(subject, activeTab);
    const typedDetailData = detailData as SubjectDetailData | null;
    const typedHistoryData = historyData as SchemaHistoryResponse | null;
    const typedDriftData = driftData as SchemaDriftResponse | null;
    const previewSchemaText = useMemo(() => {
        if (!versionPreview?.schema_str) {
            return '';
        }
        try {
            return JSON.stringify(JSON.parse(versionPreview.schema_str), null, 2);
        } catch {
            return versionPreview.schema_str;
        }
    }, [versionPreview]);
    const comparisonFromSchema = useMemo(() => {
        if (!versionComparison?.from_schema) {
            return '';
        }
        try {
            return JSON.stringify(JSON.parse(versionComparison.from_schema), null, 2);
        } catch {
            return versionComparison.from_schema;
        }
    }, [versionComparison]);
    const comparisonToSchema = useMemo(() => {
        if (!versionComparison?.to_schema) {
            return '';
        }
        try {
            return JSON.stringify(JSON.parse(versionComparison.to_schema), null, 2);
        } catch {
            return versionComparison.to_schema;
        }
    }, [versionComparison]);

    // Initial value setup for edit
    const startEditing = () => {
        if (typedDetailData) {
            let schema = typedDetailData.schema_str;
            try {
                if (schema) {
                    schema = JSON.stringify(JSON.parse(schema), null, 2);
                }
            } catch {
                // Not JSON, keep as is
            }
            setEditedSchema(schema);
            setCompatibility(typedDetailData.compatibility_mode || '');
            setIsEditing(true);
            setRollbackTargetVersion(null);
            setActiveTab('overview');
        }
    };

    const startEditingSettings = () => {
        if (!typedDetailData) return;
        setSettingsOwner(typedDetailData.owner || '');
        setSettingsDoc(typedDetailData.doc || '');
        setSettingsDescription(typedDetailData.description || '');
        setSettingsTags((typedDetailData.tags || []).join(', '));
        setSettingsCompatibility(typedDetailData.compatibility_mode || '');
        setIsEditingSettings(true);
    };

    const handlePlan = async () => {
        if (!subject) return;
        if (!compatibility) {
            toast.error('Select compatibility explicitly before planning a schema change');
            return;
        }
        try {
            setIsPlanning(true);
            const activeRegistry = await requireActiveRegistry();

            if (!activeRegistry) {
                return;
            }

            const res = await schemasAPI.planChange(activeRegistry.registry_id, {
                subject,
                new_schema: editedSchema,
                compatibility
            });
            setPlanResult(res.data as SchemaPlanResult);
            setRollbackTargetVersion(null);
            toast.success('Change plan generated');
        } catch (error) {
            toast.error(describeGovernanceError(error, 'Planning failed'));
        } finally {
            setIsPlanning(false);
        }
    };

    const handleApply = async () => {
        if (!planResult || !subject) return;
        try {
            const activeRegistry = await requireActiveRegistry();
            if (!activeRegistry) {
                return;
            }

            const approvalOverride = promptApprovalOverride(
                rollbackTargetVersion !== null
                    ? `schema rollback for ${subject} to v${rollbackTargetVersion}`
                    : `schema apply for ${subject}`,
            );
            if (!approvalOverride) {
                toast.error('Approval evidence is required for this schema change');
                return;
            }

            if (rollbackTargetVersion !== null) {
                const rollbackPayload: RollbackExecutePayload = {
                    subject,
                    version: rollbackTargetVersion,
                    reason: `Rollback to v${rollbackTargetVersion}`,
                    approvalOverride,
                };
                await schemasAPI.rollbackExecute(activeRegistry.registry_id, rollbackPayload);
                toast.success(`Schema rollback executed from v${rollbackTargetVersion}`);
                setIsEditing(false);
                setPlanResult(null);
                setRollbackTargetVersion(null);
                reload();
                return;
            }

            // Format as batch request (backend expects batch)
            const batchRequest: SchemaBatchApplyRequest = {
                env: subject.split('.')[0] || 'dev',
                change_id: planResult.change_id,
                approvalOverride,
                items: planResult.plan.map((item) => ({
                    subject: item.subject,
                    type: item.diff.schema_type || 'AVRO',
                    compatibility: planResult.compatibility.find((report) => report.subject === item.subject)?.mode ?? compatibility,
                    schema: editedSchema,
                }))
            };

            await schemasAPI.apply(activeRegistry.registry_id, batchRequest);
            toast.success('Schema successfully updated to next version');
            setIsEditing(false);
            setPlanResult(null);
            setRollbackTargetVersion(null);
            reload(); // Refresh data
        } catch (error) {
            toast.error(describeGovernanceError(error, 'Apply failed'));
        }
    };

    const handleRollback = async (version: number) => {
        if (!subject || !confirmSchemaGovernanceAction(`Rollback to v${version}?`)) return;
        try {
            const activeRegistry = await requireActiveRegistry();
            if (!activeRegistry) {
                return;
            }

            const res = await schemasAPI.planRollback(activeRegistry.registry_id, {
                subject,
                version
            });
            const plan = res.data as SchemaPlanResult;

            // For now, let's just use the planResult flow but specifically for rollback
            setPlanResult(plan);
            setRollbackTargetVersion(version);
            // In rollback case, we need the schema from the plan
            // The plan result for rollback contains the old schema content
            let oldSchema = plan.plan[0]?.schema ?? plan.plan[0]?.schema_definition;
            if (!oldSchema) {
                toast.error('Rollback plan did not include schema content');
                return;
            }
            if (oldSchema) {
                try {
                    oldSchema = JSON.stringify(JSON.parse(oldSchema), null, 2);
                } catch {
                    // Not JSON
                }
                setEditedSchema(oldSchema);
            }

            setActiveTab('overview');
            setIsEditing(true);
        } catch (error) {
            toast.error(describeGovernanceError(error, 'Rollback plan failed'));
        }
    };

    const handleDelete = async () => {
        if (!subject || !confirmSchemaGovernanceAction(`Are you sure you want to delete subject "${subject}"? This will remove all versions.`)) return;

        try {
            setIsDeleting(true);
            const activeRegistry = await requireActiveRegistry();

            if (!activeRegistry) {
                return;
            }

            await schemasAPI.delete(activeRegistry.registry_id, subject);
            toast.success('Subject deleted successfully');
            navigate('/schemas');
        } catch (error) {
            const errorMsg = describeGovernanceError(error, 'Delete failed');
            const errorStatus = extractErrorStatus(error);

            // Check if it's a safety violation that can be forced
            if (errorStatus === 400 && errorMsg.includes('안전하지 않습니다')) {
                setDeleteWarning(errorMsg);
                setShowForceDeleteModal(true);
            } else {
                console.error('Delete failed', error);
                toast.error(errorMsg);
            }
        } finally {
            setIsDeleting(false);
        }
    };

    const handleSaveSettings = async () => {
        if (!subject) return;
        try {
            const activeRegistry = await requireActiveRegistry();
            if (!activeRegistry) {
                return;
            }
            const payload: SchemaSettingsPayload = {
                owner: settingsOwner || null,
                doc: settingsDoc || null,
                description: settingsDescription || null,
                tags: settingsTags
                    .split(',')
                    .map((item) => item.trim())
                    .filter(Boolean),
                compatibilityMode: settingsCompatibility || null,
            };
            await schemasAPI.updateSettings(activeRegistry.registry_id, subject, payload);
            toast.success('Schema settings updated');
            setIsEditingSettings(false);
            reload();
        } catch (error) {
            toast.error(describeGovernanceError(error, 'Schema settings update failed'));
        }
    };

    const handleDownloadLatest = async () => {
        if (!subject) return;
        try {
            const activeRegistry = await requireActiveRegistry();
            if (!activeRegistry) {
                return;
            }
            const response = await schemasAPI.exportLatest(activeRegistry.registry_id, subject);
            const filename = extractDownloadFilename(
                response.headers as Record<string, string | undefined> | undefined,
                `${subject}.schema`,
            );
            downloadText(typeof response.data === 'string' ? response.data : String(response.data), filename);
            toast.success('Latest schema downloaded');
        } catch (error) {
            toast.error(describeGovernanceError(error, 'Latest schema export failed'));
        }
    };

    const handleDownloadVersion = async (version: number) => {
        if (!subject) return;
        try {
            const activeRegistry = await requireActiveRegistry();
            if (!activeRegistry) {
                return;
            }
            const response = await schemasAPI.exportVersion(activeRegistry.registry_id, subject, version);
            const filename = extractDownloadFilename(
                response.headers as Record<string, string | undefined> | undefined,
                `${subject}.v${version}.schema`,
            );
            downloadText(typeof response.data === 'string' ? response.data : String(response.data), filename);
            toast.success(`Downloaded v${version}`);
        } catch (error) {
            toast.error(describeGovernanceError(error, 'Schema version export failed'));
        }
    };

    const handlePreviewVersion = async (version: number) => {
        if (!subject) return;
        try {
            setIsPreviewLoading(true);
            const activeRegistry = await requireActiveRegistry();
            if (!activeRegistry) {
                return;
            }
            const response = await schemasAPI.getVersion(activeRegistry.registry_id, subject, version);
            setVersionPreview(response.data as SchemaVersionDetailResponse);
        } catch (error) {
            toast.error(describeGovernanceError(error, 'Schema version preview failed'));
        } finally {
            setIsPreviewLoading(false);
        }
    };

    const handleCompareVersion = async (fromVersion: number, toVersion: number) => {
        if (!subject) return;
        try {
            setIsComparisonLoading(true);
            const activeRegistry = await requireActiveRegistry();
            if (!activeRegistry) {
                return;
            }
            const response = await schemasAPI.compareVersions(
                activeRegistry.registry_id,
                subject,
                fromVersion,
                toVersion,
            );
            setVersionComparison(response.data as SchemaVersionCompareResponse);
        } catch (error) {
            toast.error(describeGovernanceError(error, 'Schema version compare failed'));
        } finally {
            setIsComparisonLoading(false);
        }
    };

    const handleConfirmForceDelete = async () => {
        if (!subject) return;

        try {
            setIsDeleting(true);
            const activeRegistry = await requireActiveRegistry();

            if (!activeRegistry) {
                return;
            }

            // Call with force=true
            await schemasAPI.delete(activeRegistry.registry_id, subject, true);
            toast.success('Subject force deleted successfully');
            setShowForceDeleteModal(false);
            navigate('/schemas');
        } catch (error) {
            console.error('Force delete failed', error);
            toast.error(describeGovernanceError(error, 'Force delete failed'));
        } finally {
            setIsDeleting(false);
        }
    };

    return (
        <div className="min-h-screen bg-[#f6f8fa]">
            {/* Header / Breadcrumbs --- */}
            <div className="bg-white border-b border-[#d0d7de] pt-4 px-8 pb-4">
                <nav className="flex items-center gap-2 text-sm text-[#57606a] mb-4">
                    <button
                        type="button"
                        onClick={() => navigate('/schemas')}
                        className="hover:text-[#0969da]"
                    >
                        Schemas
                    </button>
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
                            {typedDetailData && (
                                <div className="flex gap-4 mt-1 text-xs text-[#57606a]">
                                    <span className="flex items-center gap-1.5">Latest: <span className="font-semibold text-[#24292f]">v{typedDetailData.version}</span></span>
                                    <span className="flex items-center gap-1.5 px-1.5 bg-[#f6f8fa] border border-[#d0d7de] rounded-md font-mono text-[10px]">{typedDetailData.schema_type}</span>
                                    {typedDetailData.owner && <span className="flex items-center gap-1.5">Owner: <span className="font-semibold text-[#24292f]">{typedDetailData.owner}</span></span>}
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
                                    onClick={handleDownloadLatest}
                                    className="bg-white border-[#d0d7de] text-[#24292f] hover:bg-[#f3f4f6]"
                                >
                                    Download Latest
                                </Button>
                                <Button
                                    variant="secondary"
                                    size="sm"
                                    onClick={startEditingSettings}
                                    className="bg-white border-[#d0d7de] text-[#24292f] hover:bg-[#f3f4f6]"
                                >
                                    Edit Metadata
                                </Button>
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
                                onClick={() => { setIsEditing(false); setPlanResult(null); setRollbackTargetVersion(null); }}
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
                                {activeTab === 'overview' && typedDetailData && (
                                    <div className="space-y-4">
                                        {!isEditing ? (
                                            <>
                                                <div className="flex items-center justify-between">
                                                    <h3 className="text-sm font-semibold text-[#24292f]">Schema Definition</h3>
                                                    <div className="flex items-center gap-2">
                                                        {typedDetailData.policy_score && (
                                                            <div className="flex items-center gap-1.5 mr-2">
                                                                <span className="text-[10px] text-gray-500 uppercase font-bold">Policy Score:</span>
                                                                <span className={`text-xs font-bold ${typedDetailData.policy_score > 0.8 ? 'text-green-600' : 'text-amber-600'}`}>
                                                                    {Math.round(typedDetailData.policy_score * 100)}%
                                                                </span>
                                                            </div>
                                                        )}
                                                        <Badge variant="outline" className="text-[10px] font-mono">v{typedDetailData.version}</Badge>
                                                    </div>
                                                </div>

                                                {/* Violations Sidebar/Section */}
                                                {typedDetailData.violations && typedDetailData.violations.length > 0 && (
                                                    <div className="mt-2 mb-6 p-4 bg-rose-50 border border-rose-100 rounded-xl space-y-3">
                                                        <div className="flex items-center gap-2 text-rose-700">
                                                            <AlertCircle className="w-4 h-4" />
                                                            <h4 className="text-xs font-bold uppercase tracking-wider">Policy Violations ({typedDetailData.violations.length})</h4>
                                                        </div>
                                                        <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                                                            {typedDetailData.violations.map((v) => (
                                                                <div key={`${v.rule}-${v.message}-${v.severity}`} className="flex items-start gap-2 text-xs bg-white p-2.5 rounded-lg border border-rose-100 shadow-sm">
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

                                                {typedDriftData && (
                                                    <div className={`mt-2 mb-6 p-4 rounded-xl space-y-3 border ${typedDriftData.has_drift ? 'bg-amber-50 border-amber-200' : 'bg-emerald-50 border-emerald-200'}`}>
                                                        <div className={`flex items-center gap-2 ${typedDriftData.has_drift ? 'text-amber-700' : 'text-emerald-700'}`}>
                                                            <AlertTriangle className="w-4 h-4" />
                                                            <h4 className="text-xs font-bold uppercase tracking-wider">
                                                                Drift Status {typedDriftData.has_drift ? '(Detected)' : '(In Sync)'}
                                                            </h4>
                                                        </div>
                                                        <div className="text-xs text-[#57606a] flex flex-wrap gap-3">
                                                            <span>Registry latest: <span className="font-semibold text-[#24292f]">v{typedDriftData.registry_latest_version}</span></span>
                                                            {typedDriftData.catalog_latest_version !== null && (
                                                                <span>Catalog latest: <span className="font-semibold text-[#24292f]">v{typedDriftData.catalog_latest_version}</span></span>
                                                            )}
                                                            {typedDriftData.observed_version !== null && (
                                                                <span>Observed usage: <span className="font-semibold text-[#24292f]">v{typedDriftData.observed_version}</span></span>
                                                            )}
                                                        </div>
                                                        {typedDriftData.drift_flags.length > 0 ? (
                                                            <ul className="space-y-1 text-xs text-[#7c5c00]">
                                                                {typedDriftData.drift_flags.map((flag) => (
                                                                    <li key={flag}>• {flag}</li>
                                                                ))}
                                                            </ul>
                                                        ) : (
                                                            <p className="text-xs text-emerald-700">Registry and catalog snapshots are currently aligned.</p>
                                                        )}
                                                    </div>
                                                )}

                                                <div className="mt-2 mb-6 p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-3">
                                                    <div className="flex items-center gap-2 text-slate-700">
                                                        <CheckCircle2 className="w-4 h-4" />
                                                        <h4 className="text-xs font-bold uppercase tracking-wider">Metadata</h4>
                                                    </div>
                                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs text-[#57606a]">
                                                        <div>
                                                            <div className="font-semibold text-[#24292f]">Owner</div>
                                                            <div>{typedDetailData.owner || 'Not set'}</div>
                                                        </div>
                                                        <div>
                                                            <div className="font-semibold text-[#24292f]">Compatibility</div>
                                                            <div>{typedDetailData.compatibility_mode || 'NONE'}</div>
                                                        </div>
                                                        <div>
                                                            <div className="font-semibold text-[#24292f]">Documentation</div>
                                                            <div>{typedDetailData.doc || 'Not set'}</div>
                                                        </div>
                                                        <div>
                                                            <div className="font-semibold text-[#24292f]">Description</div>
                                                            <div>{typedDetailData.description || 'Not set'}</div>
                                                        </div>
                                                        <div className="md:col-span-2">
                                                            <div className="font-semibold text-[#24292f]">Tags</div>
                                                            <div className="flex flex-wrap gap-2 mt-1">
                                                                {(typedDetailData.tags || []).length > 0 ? (
                                                                    (typedDetailData.tags || []).map((tag) => (
                                                                        <Badge key={tag} variant="outline" className="text-[10px] font-mono">
                                                                            {tag}
                                                                        </Badge>
                                                                    ))
                                                                ) : (
                                                                    <span>No tags</span>
                                                                )}
                                                            </div>
                                                        </div>
                                                    </div>
                                                </div>

                                                <OverviewCode schemaStr={typedDetailData.schema_str} />
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
                                                                    <option value="">Select compatibility</option>
                                                                    {['NONE', 'BACKWARD', 'BACKWARD_TRANSITIVE', 'FORWARD', 'FORWARD_TRANSITIVE', 'FULL', 'FULL_TRANSITIVE'].map(m => (
                                                                        <option key={m} value={m}>{m}</option>
                                                                    ))}
                                                                </select>
                                                                <span className="text-[10px] text-amber-700">No hidden default</span>
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
                                                                    const newValue = `${value.substring(0, start)}  ${value.substring(end)}`;
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
                                                        onApply={handleApply}
                                                        onCancel={() => setPlanResult(null)}
                                                    />
                                                )}
                                            </div>
                                        )}
                                    </div>
                                )}

                                {activeTab === 'history' && typedHistoryData && (
                                    <div className="space-y-4">
                                        <div className="flex items-center justify-between mb-2">
                                            <h3 className="text-sm font-semibold text-[#24292f]">Version Activity</h3>
                                        </div>
                                        <div className="border border-[#d0d7de] rounded-lg overflow-hidden">
                                            {typedHistoryData.history.map((item, idx) => (
                                                <div
                                                    key={item.version}
                                                    className={`p-4 flex items-center justify-between hover:bg-[#f6f8fa] transition-colors ${idx !== typedHistoryData.history.length - 1 ? 'border-b border-[#d0d7de]' : ''}`}
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
                                                        <Button
                                                            variant="secondary"
                                                            size="sm"
                                                            onClick={() => handlePreviewVersion(item.version)}
                                                            className="h-8 text-[11px] px-3 border-[#d0d7de] text-[#24292f] hover:bg-[#f6f8fa]"
                                                        >
                                                            Preview
                                                        </Button>
                                                        <Button
                                                            variant="secondary"
                                                            size="sm"
                                                            onClick={() => handleDownloadVersion(item.version)}
                                                            className="h-8 text-[11px] px-3 border-[#d0d7de] text-[#24292f] hover:bg-[#f6f8fa]"
                                                        >
                                                            Download
                                                        </Button>
                                                        {idx > 0 && typedHistoryData.history[0] && (
                                                            <Button
                                                                variant="secondary"
                                                                size="sm"
                                                                onClick={() => handleCompareVersion(item.version, typedHistoryData.history[0].version)}
                                                                className="h-8 text-[11px] px-3 border-[#d0d7de] text-[#24292f] hover:bg-[#f6f8fa]"
                                                            >
                                                                Compare to Latest
                                                            </Button>
                                                        )}
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
                                        This schema has deletion warnings. Review them carefully before forcing deletion.
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

            {isEditingSettings && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
                    <div className="bg-white rounded-xl shadow-xl max-w-2xl w-full overflow-hidden border border-[#d0d7de]">
                        <div className="px-6 py-4 border-b border-[#d0d7de] flex items-center justify-between">
                            <h3 className="text-lg font-bold text-[#24292f]">Edit Schema Metadata</h3>
                            <Button variant="ghost" size="sm" onClick={() => setIsEditingSettings(false)}>
                                Close
                            </Button>
                        </div>
                        <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-4">
                            <label htmlFor="schema-settings-owner" className="text-sm text-[#24292f]">
                                <div className="mb-1 font-semibold">Owner</div>
                                <input id="schema-settings-owner" value={settingsOwner} onChange={(e) => setSettingsOwner(e.target.value)} className="w-full border border-[#d0d7de] rounded-md px-3 py-2" />
                            </label>
                            <label htmlFor="schema-settings-compatibility" className="text-sm text-[#24292f]">
                                <div className="mb-1 font-semibold">Compatibility</div>
                                <select id="schema-settings-compatibility" value={settingsCompatibility} onChange={(e) => setSettingsCompatibility(e.target.value)} className="w-full border border-[#d0d7de] rounded-md px-3 py-2 bg-white">
                                    <option value="">Leave unset</option>
                                    {['NONE', 'BACKWARD', 'BACKWARD_TRANSITIVE', 'FORWARD', 'FORWARD_TRANSITIVE', 'FULL', 'FULL_TRANSITIVE'].map(m => (
                                        <option key={m} value={m}>{m}</option>
                                    ))}
                                </select>
                                <p className="mt-1 text-xs text-amber-700">No implicit compatibility default is applied.</p>
                            </label>
                            <label htmlFor="schema-settings-doc" className="text-sm text-[#24292f] md:col-span-2">
                                <div className="mb-1 font-semibold">Documentation URL / Notes</div>
                                <input id="schema-settings-doc" value={settingsDoc} onChange={(e) => setSettingsDoc(e.target.value)} className="w-full border border-[#d0d7de] rounded-md px-3 py-2" />
                            </label>
                            <label htmlFor="schema-settings-description" className="text-sm text-[#24292f] md:col-span-2">
                                <div className="mb-1 font-semibold">Description</div>
                                <textarea id="schema-settings-description" value={settingsDescription} onChange={(e) => setSettingsDescription(e.target.value)} className="w-full border border-[#d0d7de] rounded-md px-3 py-2 min-h-[100px]" />
                            </label>
                            <label htmlFor="schema-settings-tags" className="text-sm text-[#24292f] md:col-span-2">
                                <div className="mb-1 font-semibold">Tags (comma separated)</div>
                                <input id="schema-settings-tags" value={settingsTags} onChange={(e) => setSettingsTags(e.target.value)} className="w-full border border-[#d0d7de] rounded-md px-3 py-2" />
                            </label>
                        </div>
                        <div className="px-6 py-4 border-t border-[#d0d7de] flex justify-end gap-3">
                            <Button variant="ghost" onClick={() => setIsEditingSettings(false)}>Cancel</Button>
                            <Button variant="primary" onClick={handleSaveSettings}>Save Metadata</Button>
                        </div>
                    </div>
                </div>
            )}

            {(versionPreview || isPreviewLoading) && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
                    <div className="bg-white rounded-xl shadow-xl max-w-5xl w-full overflow-hidden border border-[#d0d7de]">
                        <div className="px-6 py-4 border-b border-[#d0d7de] flex items-center justify-between">
                            <div>
                                <h3 className="text-lg font-bold text-[#24292f]">
                                    {isPreviewLoading ? 'Loading version preview…' : `${subject} v${versionPreview?.version}`}
                                </h3>
                                {versionPreview && (
                                    <p className="text-xs text-[#57606a] mt-1">
                                        {versionPreview.schema_type} · schema id {versionPreview.schema_id}
                                        {versionPreview.author ? ` · ${versionPreview.author}` : ''}
                                    </p>
                                )}
                            </div>
                            <div className="flex items-center gap-2">
                                {versionPreview && (
                                    <Button
                                        variant="secondary"
                                        size="sm"
                                        onClick={() => handleDownloadVersion(versionPreview.version)}
                                    >
                                        Download
                                    </Button>
                                )}
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => setVersionPreview(null)}
                                >
                                    Close
                                </Button>
                            </div>
                        </div>
                        <div className="p-6">
                            {isPreviewLoading ? (
                                <div className="flex justify-center py-20">
                                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#0969da]" />
                                </div>
                            ) : versionPreview ? (
                                <div className="space-y-4">
                                    <div className="flex flex-wrap gap-2 text-xs text-[#57606a]">
                                        <Badge variant="outline" className="text-[10px] font-mono">v{versionPreview.version}</Badge>
                                        {versionPreview.compatibility_mode && (
                                            <Badge variant="outline" className="text-[10px] font-mono">
                                                {versionPreview.compatibility_mode}
                                            </Badge>
                                        )}
                                        {versionPreview.owner && <span>Owner: <span className="font-semibold text-[#24292f]">{versionPreview.owner}</span></span>}
                                    </div>
                                    <OverviewCode schemaStr={previewSchemaText} />
                                </div>
                            ) : null}
                        </div>
                    </div>
                </div>
            )}

            {(versionComparison || isComparisonLoading) && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
                    <div className="bg-white rounded-xl shadow-xl max-w-6xl w-full overflow-hidden border border-[#d0d7de]">
                        <div className="px-6 py-4 border-b border-[#d0d7de] flex items-center justify-between">
                            <div>
                                <h3 className="text-lg font-bold text-[#24292f]">
                                    {isComparisonLoading
                                        ? 'Loading comparison…'
                                        : `${subject} comparison v${versionComparison?.from_version} → v${versionComparison?.to_version}`}
                                </h3>
                                {versionComparison && (
                                    <p className="text-xs text-[#57606a] mt-1">
                                        {versionComparison.schema_type}
                                        {versionComparison.compatibility_mode ? ` · ${versionComparison.compatibility_mode}` : ''}
                                    </p>
                                )}
                            </div>
                            <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => setVersionComparison(null)}
                            >
                                Close
                            </Button>
                        </div>
                        <div className="p-6">
                            {isComparisonLoading ? (
                                <div className="flex justify-center py-20">
                                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#0969da]" />
                                </div>
                            ) : versionComparison ? (
                                <div className="space-y-4">
                                    <div className="flex flex-wrap items-center gap-2 text-xs text-[#57606a]">
                                        <Badge variant="outline" className="text-[10px] font-mono">
                                            {versionComparison.changed ? 'Changed' : 'No Change'}
                                        </Badge>
                                        <Badge variant="outline" className="text-[10px] font-mono">
                                            {versionComparison.diff_type}
                                        </Badge>
                                    </div>
                                    <div className="bg-[#f6f8fa] border border-[#d0d7de] rounded-lg p-4">
                                        <h4 className="text-sm font-semibold text-[#24292f] mb-2">Change Summary</h4>
                                        <ul className="space-y-1 text-sm text-[#57606a]">
                                            {versionComparison.changes.map((change) => (
                                                <li key={change}>• {change}</li>
                                            ))}
                                        </ul>
                                    </div>
                                    <JsonDiffHelper oldStr={comparisonFromSchema} newStr={comparisonToSchema} />
                                </div>
                            ) : null}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
