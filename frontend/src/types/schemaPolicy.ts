export type SchemaPolicyType = "lint" | "guardrail";
export type SchemaPolicyStatus = "draft" | "active" | "archived";

export interface SchemaPolicyRule {
  enabled?: boolean;
  severity?: string;
  [key: string]: unknown;
}

export interface SchemaPolicyContent {
  rules?: Record<string, SchemaPolicyRule>;
  guardrails?: {
    allowed_compatibility?: string[];
    [key: string]: unknown;
  };
  [key: string]: unknown;
}

export interface SchemaPolicyRecord {
  policy_id: string;
  name: string;
  description: string;
  policy_type: SchemaPolicyType;
  status: SchemaPolicyStatus;
  version: number;
  target_environment: string;
  content: SchemaPolicyContent;
  created_by: string;
  created_at: string;
}

export interface SchemaPolicyFormInput {
  name: string;
  description: string;
  policy_type: SchemaPolicyType;
  target_environment: string;
  content: SchemaPolicyContent;
  created_by?: string;
}
