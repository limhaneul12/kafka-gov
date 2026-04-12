// Common Types
export interface APIResponse<T> {
  data: T;
  message?: string;
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

// Policy Types
export interface Policy {
  policy_id: string;
  policy_type: string;
  name: string;
  description: string | null;
  content: Record<string, unknown>;
  version: number;
  status: "DRAFT" | "ACTIVE" | "ARCHIVED";
  created_by: string;
  created_at: string;
  target_environment: string;
  updated_at: string | null;
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
  metadata: Record<string, unknown> | null;
}
