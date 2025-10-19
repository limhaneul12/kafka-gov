// Common Types
export interface APIResponse<T> {
  data: T;
  message?: string;
}

// Topic Types
export interface Topic {
  name: string;
  owner: string | null;
  doc: string | null;
  tags: string[];
  partition_count: number | null;
  replication_factor: number | null;
  environment: string;
}

export interface TopicListResponse {
  topics: Topic[];
}

// Schema Types
export interface SchemaArtifact {
  subject: string;
  version: number;
  storage_url: string;
  checksum: string;
  schema_type: string;
  compatibility_mode: string | null;
  owner: string | null;
}

// Cluster Types
export interface KafkaCluster {
  cluster_id: string;
  name: string;
  bootstrap_servers: string;
  description: string | null;
  security_protocol: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface SchemaRegistry {
  registry_id: string;
  name: string;
  url: string;
  description: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ObjectStorage {
  storage_id: string;
  name: string;
  endpoint_url: string;
  description: string | null;
  bucket_name: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface KafkaConnect {
  connect_id: string;
  cluster_id: string;
  name: string;
  url: string;
  description: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

// Connect Types
export interface Connector {
  name: string;
  config: Record<string, any>;
  tasks: ConnectorTask[];
  type: string;
}

export interface ConnectorTask {
  connector: string;
  task: number;
  id: string;
  state: string;
  worker_id: string;
}

export interface ConnectorStatus {
  name: string;
  connector: {
    state: string;
    worker_id: string;
  };
  tasks: Array<{
    id: number;
    state: string;
    worker_id: string;
  }>;
  type: string;
}

// Policy Types
export interface Policy {
  policy_id: string;
  policy_type: string;
  name: string;
  description: string | null;
  content: Record<string, any>;
  version: number;
  status: "DRAFT" | "ACTIVE" | "ARCHIVED";
  created_by: string;
  created_at: string;
  updated_at: string;
}

// Audit Types
export interface AuditLog {
  activity_type: string;
  action: string;
  target: string;
  message: string;
  actor: string;
  team: string | null;
  timestamp: string;
  metadata: Record<string, any> | null;
}

// Analysis Types
export interface Statistics {
  topic_count: number;
  schema_count: number;
  correlation_count: number;
}

export interface TopicSchemaCorrelation {
  correlation_id: string;
  topic_name: string;
  key_schema_subject: string | null;
  value_schema_subject: string | null;
  environment: string;
  link_source: string;
  confidence_score: number;
}

export interface SchemaImpactAnalysis {
  subject: string;
  affected_topics: string[];
  total_impact_count: number;
  risk_level: string;
  warnings: string[];
}
