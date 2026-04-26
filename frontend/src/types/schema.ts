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
    violations?: Array<{ rule: string; message: string; severity: string }>;
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

export interface SchemaVersionReferenceResponse {
    name: string;
    subject: string;
    version: number;
}

export interface SchemaVersionSummaryResponse {
    version: number;
    schema_id: number;
    schema_type: string;
    hash: string;
    canonical_hash: string | null;
    created_at: string | null;
    author: string | null;
    commit_message: string | null;
}

export interface SchemaVersionListResponse {
    subject: string;
    versions: SchemaVersionSummaryResponse[];
}

export interface SchemaVersionDetailResponse extends SchemaVersionSummaryResponse {
    subject: string;
    schema_str: string;
    references: SchemaVersionReferenceResponse[];
    owner: string | null;
    compatibility_mode: string | null;
}

export interface SchemaVersionCompareResponse {
    subject: string;
    from_version: number;
    to_version: number;
    changed: boolean;
    diff_type: string;
    changes: string[];
    schema_type: string;
    compatibility_mode: string | null;
    from_schema: string | null;
    to_schema: string | null;
}

export interface SchemaDriftResponse {
    subject: string;
    registry_latest_version: number;
    registry_canonical_hash: string | null;
    catalog_latest_version: number | null;
    catalog_canonical_hash: string | null;
    observed_version: number | null;
    last_synced_at: string | null;
    drift_flags: string[];
    has_drift: boolean;
}

export interface ApprovalRequestResponse {
    request_id: string;
    resource_type: string;
    resource_name: string;
    change_type: string;
    change_ref: string | null;
    summary: string;
    justification: string;
    requested_by: string;
    status: string;
    approver: string | null;
    decision_reason: string | null;
    metadata: Record<string, unknown> | null;
    requested_at: string;
    decided_at: string | null;
}

export interface AuditActivityResponse {
    activity_type: string;
    action: string;
    target: string;
    message: string;
    actor: string;
    team: string | null;
    timestamp: string;
    metadata: Record<string, unknown> | null;
}

export interface SchemaArtifactResponse {
    subject: string;
    version: number | null;
    storage_url: string | null;
    checksum: string | null;
    schema_type: string | null;
    compatibility_mode: string | null;
    owner: string | null;
    created_at: string | null;
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
