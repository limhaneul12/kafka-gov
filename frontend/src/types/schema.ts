export interface GovernanceScore {
    compatibility_pass_rate: number;
    documentation_coverage: number;
    average_lint_score: number;
    total_score: number;
}

export interface SubjectStat {
    subject: string;
    owner: string | null;
    version_count: number;
    last_updated: string;
    compatibility_mode: string | null;
    lint_score: number;
    has_doc: boolean;
}

export interface DashboardResponse {
    total_subjects: number;
    total_versions: number;
    orphan_subjects: number;
    scores: GovernanceScore;
    top_subjects: SubjectStat[];
}

export interface SchemaHistoryItem {
    version: number;
    schema_id: number;
    created_at: string | null;
    diff_type: string;
    author: string | null;
    commit_message: string | null;
}

export interface SchemaHistoryResponse {
    subject: string;
    history: SchemaHistoryItem[];
}

export interface GraphNode {
    id: string;
    type: 'SCHEMA' | 'TOPIC' | 'CONSUMER';
    label: string;
    metadata?: Record<string, string | number>;
}

export interface GraphLink {
    source: string;
    target: string;
    relation: string;
}

export interface ImpactGraphResponse {
    subject: string;
    nodes: GraphNode[];
    links: GraphLink[];
}

export interface SchemaArtifactResponse {
    subject: string;
    version: number | null;
    storage_url: string | null;
    checksum: string | null;
    schema_type: string | null;
    compatibility_mode: string | null;
    owner: string | null;
}

export interface SchemaSearchResponse {
    items: SchemaArtifactResponse[];
    total: number;
    page: number;
    limit: number;
}

export interface SchemaSearchParams {
    query?: string;
    owner?: string;
    page?: number;
    limit?: number;
}
