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
