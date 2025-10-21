/**
 * Kafka Connect Module Types
 */

export interface KafkaConnect {
  connect_id: string;
  name: string;
  url: string;
  is_active: boolean;
}

export interface ConnectorStatus {
  name: string;
  type: "source" | "sink";
  state: "RUNNING" | "PAUSED" | "FAILED" | "UNASSIGNED";
  worker_id: string;
  tasks: ConnectorTask[];
}

export interface ConnectorTask {
  id: number;
  state: string;
  worker_id: string;
}

export interface ConnectorConfig {
  name: string;
  config: Record<string, string>;
}
