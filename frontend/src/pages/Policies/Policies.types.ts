/**
 * Policies Module Types
 */

export type PolicyStatus = "DRAFT" | "ACTIVE" | "ARCHIVED";
export type PolicyType = "naming" | "guardrail";

export interface PolicyVersion {
  policy_id: string;
  policy_type: PolicyType;
  version: number;
  status: PolicyStatus;
  name: string;
  description: string;
  content: Record<string, unknown>;
  created_by: string;
  created_at: string;
  target_environment: string;
  updated_at: string | null;
  activated_at: string | null;
}

export interface PolicyDetailModalProps {
  isOpen: boolean;
  onClose: () => void;
  policyId: string;
  onEdit: (policy: PolicyVersion) => void;
  onRefresh: () => void;
  autoShowVersions?: boolean;
}

export interface PolicyVersionListProps {
  versions: PolicyVersion[];
  currentVersion: number;
  onVersionSelect: (version: PolicyVersion) => void;
  onActivate: (policyId: string, version: number) => void;
  onArchive: (policyId: string, version: number) => void;
  onDelete: (policyId: string, version: number) => void;
  onCompare: (baseVersion: number, targetVersion: number) => void;
}

export interface PolicyContentViewProps {
  policy: PolicyVersion;
  onEdit: () => void;
}

export interface PolicyDiffViewProps {
  baseVersion: PolicyVersion;
  targetVersion: PolicyVersion;
  onClose: () => void;
}
