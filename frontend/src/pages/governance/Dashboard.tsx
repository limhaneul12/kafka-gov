import React, { useEffect, useState } from 'react';
import {
    Cell,
    Legend,
    Pie,
    PieChart,
    ResponsiveContainer,
    Tooltip,
} from 'recharts';
import {
    BadgeCheck,
    FileText,
    ShieldAlert,
    Users,
    Activity,
    Server,
    Hash,
    Clock,
    AlertTriangle,
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import schemaApi from '../../services/schemaApi';
import type { DashboardResponse, SubjectStat } from '../../types/schema';
import { clustersAPI, metricsAPI } from '../../services/api';

// --- Components ---

const StatCard = ({
    title,
    value,
    icon: Icon,
    trend,
    color,
}: {
    title: string;
    value: string | number;
    icon: React.ElementType;
    trend?: string;
    color: string;
}) => (
    <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-100 flex items-start justify-between">
        <div>
            <p className="text-sm font-medium text-slate-500 mb-1">{title}</p>
            <h3 className="text-2xl font-bold text-slate-800">{value}</h3>
            {trend && <p className="text-xs text-emerald-600 mt-2 font-medium">{trend}</p>}
        </div>
        <div className={`p-3 rounded-lg ${color}`}>
            <Icon className="w-6 h-6 text-white" />
        </div>
    </div>
);

const ScoreCard = ({
    title,
    score,
    description,
}: {
    title: string;
    score: number;
    description: string;
}) => {
    const percentage = Math.round(score * 100);
    let colorClass = 'text-emerald-500';
    if (percentage < 50) colorClass = 'text-rose-500';
    else if (percentage < 80) colorClass = 'text-amber-500';

    return (
        <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-100 flex flex-col items-center text-center">
            <div className="relative w-24 h-24 mb-4">
                <svg transform="rotate(-90)" className="w-full h-full">
                    <circle
                        cx="48"
                        cy="48"
                        r="40"
                        stroke="currentColor"
                        strokeWidth="8"
                        fill="transparent"
                        className="text-slate-100"
                    />
                    <circle
                        cx="48"
                        cy="48"
                        r="40"
                        stroke="currentColor"
                        strokeWidth="8"
                        fill="transparent"
                        strokeDasharray={251.2}
                        strokeDashoffset={251.2 - (251.2 * percentage) / 100}
                        className={colorClass}
                        strokeLinecap="round"
                    />
                </svg>
                <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2">
                    <span className={`text-2xl font-bold ${colorClass}`}>{percentage}%</span>
                </div>
            </div>
            <h4 className="text-lg font-semibold text-slate-800 mb-1">{title}</h4>
            <p className="text-sm text-slate-500">{description}</p>
        </div>
    );
};

const TopSchemasTable = ({ schemas }: { schemas: SubjectStat[] }) => (
    <div className="bg-white rounded-xl shadow-sm border border-slate-100 overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-100 bg-slate-50/50">
            <h3 className="font-semibold text-slate-800">Top Schemas by Quality</h3>
        </div>
        <div className="overflow-x-auto">
            <table className="w-full">
                <thead className="bg-slate-50 text-slate-500 text-xs uppercase font-medium">
                    <tr>
                        <th className="px-6 py-3 text-left">Subject</th>
                        <th className="px-6 py-3 text-left">Owner</th>
                        <th className="px-6 py-3 text-center">Versions</th>
                        <th className="px-6 py-3 text-center">Lint Score</th>
                        <th className="px-6 py-3 text-center">Docs</th>
                    </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                    {schemas.map((schema) => (
                        <tr key={schema.subject} className="hover:bg-slate-50 transition-colors">
                            <td className="px-6 py-4 text-sm font-medium text-slate-800">
                                {schema.subject}
                            </td>
                            <td className="px-6 py-4 text-sm text-slate-500">
                                {schema.owner || <span className="text-slate-300 italic">Unassigned</span>}
                            </td>
                            <td className="px-6 py-4 text-sm text-center">
                                <span className="bg-slate-100 text-slate-600 px-2 py-1 rounded text-xs font-semibold">
                                    v{schema.version_count}
                                </span>
                            </td>
                            <td className="px-6 py-4 text-sm text-center">
                                <div className="flex items-center justify-center gap-2">
                                    <div className="w-16 h-2 bg-slate-100 rounded-full overflow-hidden">
                                        <div
                                            className={`h-full rounded-full ${schema.lint_score > 0.8
                                                ? 'bg-emerald-500'
                                                : schema.lint_score > 0.5
                                                    ? 'bg-amber-500'
                                                    : 'bg-rose-500'
                                                }`}
                                            style={{ width: `${schema.lint_score * 100}%` }}
                                        />
                                    </div>
                                    <span className="text-xs font-medium text-slate-600">
                                        {Math.round(schema.lint_score * 100)}
                                    </span>
                                </div>
                            </td>
                            <td className="px-6 py-4 text-sm text-center">
                                {schema.has_doc ? (
                                    <span className="text-emerald-500">
                                        <BadgeCheck className="w-5 h-5 mx-auto" />
                                    </span>
                                ) : (
                                    <span className="text-slate-300">
                                        <div className="w-5 h-5 mx-auto border-2 border-slate-200 rounded-full" />
                                    </span>
                                )}
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    </div>
);

// --- Main Page ---

// ... components ...

const RecentActivity = ({ activities }: { activities: any[] }) => (
    <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-100 flex flex-col h-full">
        <h3 className="font-semibold text-slate-800 mb-6 flex items-center gap-2">
            <Clock className="w-5 h-5 text-indigo-500" />
            Recent Activity
        </h3>
        <div className="flex-1 overflow-y-auto space-y-4 pr-1 scrollbar-thin">
            {activities.length === 0 ? (
                <div className="text-center py-10 text-slate-400 text-sm italic">
                    No recent activity found
                </div>
            ) : (
                activities.slice(0, 10).map((activity, idx) => (
                    <div key={activity.audit_id || idx} className="flex gap-3 border-l-2 border-slate-100 pl-4 relative text-sm">
                        <div className="absolute -left-[5px] top-1 w-2 h-2 rounded-full bg-indigo-400" />
                        <div>
                            <p className="text-slate-800 font-medium leading-snug">
                                {activity.action_type} - {activity.resource_name}
                            </p>
                            <div className="flex gap-2 text-xs text-slate-400 mt-1">
                                <span>{activity.actor_id}</span>
                                <span>•</span>
                                <span>{new Date(activity.timestamp).toLocaleTimeString()}</span>
                            </div>
                        </div>
                    </div>
                ))
            )}
        </div>
    </div>
);

const emptyData: DashboardResponse = {
    total_subjects: 0,
    total_versions: 0,
    orphan_subjects: 0,
    scores: {
        total_score: 0,
        compatibility_pass_rate: 0,
        documentation_coverage: 0,
        average_lint_score: 0
    },
    top_subjects: []
};

export default function GovernanceDashboard() {
    const [data, setData] = useState<DashboardResponse | null>(null);
    const [kafkaStats, setKafkaStats] = useState<{ topics: number, brokers: number, clusters: number } | null>(null);
    const [recentAudit, setRecentAudit] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [retryCount, setRetryCount] = useState(0);

    const { t } = useTranslation();

    useEffect(() => {
        const fetchData = async () => {
            if (retryCount === 0) setLoading(true);
            try {
                // parallel fetch for Kafka, Schema, and Audit info
                const [registriesRes, clustersRes, auditRes] = await Promise.all([
                    clustersAPI.listRegistries(),
                    clustersAPI.listKafka(),
                    // Optional audit fetch
                    fetch('/api/v1/audit/recent').then(res => res.ok ? res.json() : [])
                ]);

                const registries = registriesRes.data;
                const clusters = clustersRes.data;
                setRecentAudit(Array.isArray(auditRes) ? auditRes : auditRes.items || []);

                // Handle Schema Registry Data
                const activeRegistry = registries?.find((r: any) => r.is_active) || registries?.[0];
                if (activeRegistry) {
                    try {
                        const result = await schemaApi.getDashboardStats(activeRegistry.registry_id);
                        setData(result);
                        setError(null);
                    } catch (e: any) {
                        console.error('Schema dashboard fetch failed', e);
                        if (retryCount < 1) {
                            setRetryCount(prev => prev + 1);
                            return;
                        }
                        setData(emptyData);
                        setError(e.response?.data?.detail || e.message);
                    }
                } else {
                    setData(emptyData);
                }

                // Handle Kafka Metrics Data ...
                const activeCluster = clusters?.find((c: any) => c.is_active) || clusters?.[0];
                if (activeCluster) {
                    try {
                        const metricsRes = await metricsAPI.getClusterMetrics(activeCluster.cluster_id);
                        setKafkaStats({
                            topics: metricsRes.data.topic_count || 0,
                            brokers: metricsRes.data.broker_count || 0,
                            clusters: clusters.length
                        });
                    } catch (e) {
                        console.error('Kafka metrics fetch failed', e);
                        setKafkaStats({ topics: 0, brokers: 0, clusters: clusters.length });
                    }
                } else {
                    setKafkaStats({ topics: 0, brokers: 0, clusters: clusters?.length || 0 });
                }

            } catch (err: any) {
                console.error('Initial metadata fetch failed', err);
                setError(err.message);
            } finally {
                setLoading(false);
            }
        };
        fetchData();
    }, [retryCount]);

    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-slate-50">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600" />
            </div>
        );
    }

    const displayData = data || emptyData;

    return (
        <div className="min-h-screen bg-slate-50 p-8 space-y-8">
            {error && (
                <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <AlertTriangle className="w-5 h-5 text-amber-600" />
                        <div>
                            <h3 className="font-semibold text-amber-900">Governance Data Partially Unavailable</h3>
                            <p className="text-sm text-amber-700">
                                {error}. Please check your connections.
                            </p>
                        </div>
                    </div>
                    <Link
                        to="/connections"
                        className="bg-white border border-amber-200 text-amber-700 px-4 py-2 rounded-lg text-sm font-medium hover:bg-amber-100 transition-colors"
                    >
                        Manage Connections
                    </Link>
                </div>
            )}

            <header className="mb-8">
                <h1 className="text-3xl font-bold text-slate-900">{t("dashboard.title")}</h1>
                <p className="text-slate-500 mt-2">
                    {t("dashboard.subtitle")}
                </p>
            </header>

            {/* 0. Infrastructure Overview */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <StatCard
                    title="Active Clusters"
                    value={kafkaStats?.clusters || 0}
                    icon={Server}
                    color="bg-slate-700"
                />
                <StatCard
                    title="Total Topics"
                    value={kafkaStats?.topics || 0}
                    icon={Hash}
                    color="bg-slate-700"
                />
                <StatCard
                    title="Live Brokers"
                    value={kafkaStats?.brokers || 0}
                    icon={Activity}
                    color="bg-slate-700"
                />
            </div>

            <div className="border-t border-slate-200 my-8 pt-8">
                <h2 className="text-xl font-bold text-slate-800 mb-6">Schema Registry Insights</h2>
            </div>

            {/* 1. Key Statistics */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                <StatCard
                    title="Total Subjects"
                    value={displayData.total_subjects}
                    icon={FileText}
                    color="bg-indigo-500"
                />
                <StatCard
                    title="Total Versions"
                    value={displayData.total_versions}
                    icon={Users} // or Layers
                    color="bg-blue-500"
                />
                <StatCard
                    title="Orphan Subjects"
                    value={displayData.orphan_subjects}
                    icon={ShieldAlert}
                    color="bg-rose-500"
                    trend={displayData.orphan_subjects > 0 ? 'Requires Attention' : 'All Clear'}
                />
                <StatCard
                    title="Overall Score"
                    value={`${Math.round(displayData.scores.total_score * 100)}`}
                    icon={BadgeCheck}
                    color="bg-emerald-500"
                    trend="Top 10% Industry"
                />
            </div>

            {/* 2. Governance Scores Breakdown */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <ScoreCard
                    title="Compatibility"
                    score={displayData.scores.compatibility_pass_rate}
                    description="Schemas passing backward compatibility checks"
                />
                <ScoreCard
                    title="Documentation"
                    score={displayData.scores.documentation_coverage}
                    description="Schemas with proper description & documentation"
                />
                <ScoreCard
                    title="Lint Quality"
                    score={displayData.scores.average_lint_score}
                    description="Adherence to naming conventions and best practices"
                />
            </div>

            {/* 3. Charts & Activity Section */}
            <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
                {/* Left: Top Schemas Table */}
                <div className="lg:col-span-2">
                    <TopSchemasTable schemas={displayData.top_subjects} />
                </div>

                {/* Middle: Ownership Chart */}
                <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-100 flex flex-col xl:col-span-1">
                    <h3 className="font-semibold text-slate-800 mb-6">Subject Ownership</h3>
                    <div className="flex-1 min-h-[300px]">
                        <ResponsiveContainer width="100%" height="100%">
                            <PieChart>
                                <Pie
                                    data={[
                                        { name: 'Payment', value: 40 },
                                        { name: 'User', value: 30 },
                                        { name: 'Product', value: 20 },
                                        { name: 'Unassigned', value: 10 },
                                    ]}
                                    cx="50%"
                                    cy="50%"
                                    innerRadius={60}
                                    outerRadius={100}
                                    fill="#8884d8"
                                    paddingAngle={5}
                                    dataKey="value"
                                >
                                    <Cell fill="#6366f1" />
                                    <Cell fill="#3b82f6" />
                                    <Cell fill="#10b981" />
                                    <Cell fill="#cbd5e1" />
                                </Pie>
                                <Tooltip />
                                <Legend verticalAlign="bottom" height={36} />
                            </PieChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                {/* Right: Recent Activity */}
                <div className="xl:col-span-1 min-h-[400px]">
                    <RecentActivity activities={recentAudit} />
                </div>
            </div>
        </div>
    );
}
