/**
 * Topics Module Types
 * Centralized type definitions for Topics feature
 */

export interface Topic {
  name: string;
  owners: string[];
  doc: string | null;
  tags: string[];
  partition_count: number;
  replication_factor: number;
  retention_ms: number;
  environment: "dev" | "stg" | "prod";
  slo: string | null;
  sla: string | null;
}

export interface CreateTopicModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (clusterId: string, yamlContent: string) => Promise<void>;
  clusterId: string;
}

export type TopicMode = "single" | "batch";

export type Environment = "dev" | "stg" | "prod";

export interface PolicyInfo {
  name: string;
  version: number;
}

export interface ActivePolicies {
  naming: PolicyInfo | null;
  guardrail: PolicyInfo | null;
}

export interface SingleTopicFormData {
  topicName: string;
  partitions: string;
  replicationFactor: string;
  retentionMs: string;
  cleanupPolicy: string;
  owner: string;
  doc: string;
  tags: string;
  environment: Environment;
}

export interface DryRunResult {
  success: boolean;
  violations?: Array<{
    rule: string;
    message: string;
  }>;
  preview?: {
    topic_name: string;
    config: Record<string, any>;
  };
}
