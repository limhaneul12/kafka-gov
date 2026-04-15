import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Badge } from '../../components/common/Badge';
import { SearchBar } from '../../components/schema/SearchBar';
import { useSchemaList } from '../../hooks/schema/useSchemaList';
import type { SchemaRegistry } from '../../types';
import type { SchemaArtifactResponse } from '../../types/schema';
import { formatDistanceToNow } from 'date-fns';

// --- Components ---

const SchemaItem = ({ schema, onClick }: { schema: SchemaArtifactResponse; onClick: () => void }) => {
    return (
        <button
            type="button"
            onClick={onClick}
            className="flex w-full items-center justify-between p-4 border-b border-[#d0d7de] hover:bg-[#f6f8fa] group transition-colors cursor-pointer last:border-b-0 text-left bg-transparent"
        >
            <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                    <BookOpen className="w-4 h-4 text-[#57606a]" />
                    <h3 className="font-bold text-[#0969da] hover:underline text-[15px] truncate max-w-[400px]">
                        {schema.subject}
                    </h3>
                    <Badge variant="outline" className="rounded-full text-[10px] font-normal border-[#d0d7de] text-[#57606a]">Public</Badge>
                </div>
                <div className="flex items-center gap-4 text-xs text-[#57606a]">
                    <span className="flex items-center gap-1">
                        <span className={`w-2.5 h-2.5 rounded-full ${schema.schema_type === 'AVRO' ? 'bg-[#3178c6]' : schema.schema_type === 'JSON' ? 'bg-[#f1e05a]' : 'bg-[#e34c26]'}`} />
                        {schema.schema_type || 'AVRO'}
                    </span>
                    <span className="flex items-center gap-1">
                        <GitCommit className="w-3.5 h-3.5" />
                        v{schema.version}
                    </span>
                    {schema.owner && (
                        <span>Owner: <span className="font-semibold text-[#24292f]">{schema.owner}</span></span>
                    )}
                    {schema.created_at && (
                        <span>• Registered {formatDistanceToNow(new Date(schema.created_at), { addSuffix: true })}</span>
                    )}
                </div>
            </div>

            <div className="flex items-center gap-3">
                <Badge
                    variant="outline"
                    className={`text-[10px] font-mono border-opacity-30 ${schema.compatibility_mode === 'BACKWARD' ? 'bg-[#f0f9ff] border-[#0969da] text-[#0969da]' :
                        schema.compatibility_mode === 'FULL' ? 'bg-[#f0fdf4] border-[#1a7f37] text-[#1a7f37]' :
                            'bg-white border-[#d0d7de] text-[#57606a]'
                        }`}
                >
                    {schema.compatibility_mode || 'NONE'}
                </Badge>
                <ChevronRight className="w-4 h-4 text-[#d0d7de] group-hover:text-[#57606a] transition-colors" />
            </div>
        </button>
    );
};

// --- Page ---

import { Plus, RefreshCw, BookOpen, GitCommit, ChevronRight, Database } from 'lucide-react';
import { Button } from '../../components/common/Button';
import UploadSchemaModal from '../../components/schema/UploadSchemaModal';
import { registryAPI, schemasAPI } from '../../services/api';
import { toast } from 'sonner';

// ... inside SchemaList ...

export default function SchemaList() {
    const navigate = useNavigate();
    const { schemas, loading, total, fetchSchemas } = useSchemaList();
    const [isUploadOpen, setIsUploadOpen] = useState(false);
    const [activeRegistryId, setActiveRegistryId] = useState<string | null>(null);

    useEffect(() => {
        fetchSchemas();
        // Get active registry for upload/sync
        registryAPI.list().then(res => {
            const active = res.data.find((registry: SchemaRegistry) => registry.is_active) || res.data[0];
            if (active) setActiveRegistryId(active.registry_id);
        });
    }, [fetchSchemas]);

    const handleSync = async () => {
        if (!activeRegistryId) {
            toast.error('No active Schema Registry found');
            return;
        }
        try {
            await schemasAPI.sync(activeRegistryId);
            toast.success('Sync successful');
            fetchSchemas();
        } catch {
            toast.error('Sync failed');
        }
    };

    const handleUpload = async (regId: string, formData: FormData) => {
        try {
            await schemasAPI.upload(regId, formData);
            toast.success('Upload successful');
            fetchSchemas();
        } catch (error: unknown) {
            toast.error('Upload failed');
            throw error;
        }
    };

    return (
        <div className="min-h-screen bg-[#f6f8fa] py-10 px-8">
            <div className="max-w-[1200px] mx-auto">
                <header className="mb-8 flex justify-between items-start">
                    <div>
                        <div className="flex items-center gap-2 mb-2 text-[#57606a]">
                            <Database className="w-5 h-5" />
                            <span className="text-sm font-semibold uppercase tracking-wide">Schema Registry</span>
                        </div>
                        <h1 className="text-2xl font-bold text-[#24292f]">Schema Subjects</h1>
                        <p className="text-sm text-[#57606a] mt-1">
                            Manage and version your registered schemas from the active Schema Registry.
                        </p>
                    </div>
                    <div className="flex gap-2">
                        <Button
                            variant="secondary"
                            size="sm"
                            icon={RefreshCw}
                            onClick={handleSync}
                            className="bg-white border-[#d0d7de] text-[#24292f] hover:bg-[#f3f4f6]"
                        >
                            Sync Registry
                        </Button>
                        <Button
                            variant="success"
                            size="sm"
                            icon={Plus}
                            onClick={() => setIsUploadOpen(true)}
                            className="bg-[#1f883d] hover:bg-[#1a7f37] text-white border-none px-4"
                        >
                            Upload Schema
                        </Button>
                    </div>
                </header>

                <UploadSchemaModal
                    isOpen={isUploadOpen}
                    onClose={() => setIsUploadOpen(false)}
                    onSubmit={handleUpload}
                    registryId={activeRegistryId || 'default'}
                />

                <div className="space-y-4">
                    <div className="flex items-center justify-between gap-4">
                        <div className="flex-1">
                            <SearchBar onSearch={fetchSchemas} />
                        </div>
                    </div>

                    <div className="bg-white rounded-lg border border-[#d0d7de] shadow-sm overflow-hidden">
                        <div className="bg-[#f6f8fa] border-b border-[#d0d7de] px-4 py-3 flex items-center justify-between text-xs text-[#57606a] font-semibold">
                            <span>{total} Subjects Available</span>
                            <div className="flex gap-4">
                                <span>Sort: Newest First</span>
                            </div>
                        </div>

                        {loading ? (
                            <div className="py-20 flex justify-center bg-white">
                                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#0969da]" />
                            </div>
                        ) : (
                            <div className="divide-y divide-[#d0d7de]">
                                {schemas.length === 0 ? (
                                    <div className="text-center py-24 bg-white">
                                        <Database className="w-12 h-12 text-[#d0d7de] mx-auto mb-4" />
                                        <p className="text-[#57606a] font-medium">No schemas found.</p>
                                        <p className="text-xs text-[#8c959f] mt-1">Try adjusting your search criteria or sync the registry.</p>
                                    </div>
                                ) : (
                                    schemas.map((schema) => (
                                        <SchemaItem
                                            key={`${schema.subject}-${schema.version}`}
                                            schema={schema}
                                            onClick={() => navigate(`/schemas/${encodeURIComponent(schema.subject)}`)}
                                        />
                                    ))
                                )}
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
