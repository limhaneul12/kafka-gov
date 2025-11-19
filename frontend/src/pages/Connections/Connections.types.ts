/**
 * Connections Module Types
 */

export interface KafkaCluster {
  cluster_id: string;
  name: string;
  bootstrap_servers: string;
  security_protocol: string;
  is_active: boolean;
}

export interface SchemaRegistry {
  registry_id: string;
  name: string;
  url: string;
  is_active: boolean;
}

export type ConnectionType = "kafka" | "registry";
