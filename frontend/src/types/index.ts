// Common Types
export interface APIResponse<T> {
  data: T;
  message?: string;
}

// Topic Types
export interface Topic {
  name: string;
  owners: string[];
  doc: string | null;
  tags: string[];
  partition_count: number | null;
  replication_factor: number | null;
  retention_ms: number | null;
  environment: string;
  slo: string | null;
  sla: string | null;
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

// Consumer Types
export interface ConsumerGroup {
  group_id: string;
  cluster_id: string;
  ts: string;
  state: string;
  partition_assignor: string | null;
  member_count: number;
  topic_count: number;
  lag_stats: {
    total_lag: number;
    mean_lag: number;
    p50_lag: number;
    p95_lag: number;
    max_lag: number;
    partition_count: number;
  };
}

export interface ConsumerGroupSummary {
  group_id: string;
  cluster_id: string;
  state: string;
  lag: {
    p50: number;
    p95: number;
    max: number;
    total: number;
  };
  rebalance_score: number;
  fairness_gini: number;
  stuck: Array<{
    topic: string;
    partition: number;
    lag: number;
  }>;
}

export interface ConsumerGroupMetrics {
  cluster_id: string;
  group_id: string;
  fairness: {
    gini_coefficient: number;
    level: string;
    member_count: number;
    avg_tp_per_member: number;
    max_tp_per_member: number;
    min_tp_per_member: number;
  };
  rebalance_score: {
    score: number;
    rebalances_per_hour: number;
    stable_ratio: number | null;
    window: string;
  } | null;
  advice: {
    assignor_recommendation: string | null;
    assignor_reason: string | null;
    static_membership_recommended: boolean;
    static_membership_reason: string | null;
    scale_recommendation: string | null;
    scale_reason: string | null;
    slo_compliance_rate: number;
    risk_eta: string | null;
  };
}

export interface ConsumerMember {
  member_id: string;
  client_id: string | null;
  client_host: string | null;
  assigned_partitions: Array<{
    topic: string;
    partition: number;
  }>;
}

export interface ConsumerPartition {
  topic: string;
  partition: number;
  committed_offset: number | null;
  latest_offset: number | null;
  lag: number | null;
  assigned_member_id: string | null;
}

export interface RebalanceEvent {
  ts: string;
  moved_partitions: number;
  join_count: number;
  leave_count: number;
  elapsed_since_prev_s: number | null;
  state: string;
}

export interface PolicyAdvice {
  assignor: {
    recommendation: string | null;
    reason: string | null;
  };
  static_membership: {
    recommended: boolean;
    reason: string | null;
  };
  scale: {
    recommendation: string | null;
    reason: string | null;
  };
  slo_compliance: number;
  risk_eta: string | null;
}

export interface TopicConsumerMapping {
  topic: string;
  consumer_groups: Array<{
    group_id: string;
    state: string;
    member_count: number;
    partitions: Array<{
      partition: number;
      assigned_member_id: string | null;
      lag: number | null;
    }>;
  }>;
}
