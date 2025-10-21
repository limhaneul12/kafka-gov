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

export interface ObjectStorage {
  storage_id: string;
  name: string;
  endpoint: string;
  bucket: string;
  is_active: boolean;
}

export interface KafkaConnect {
  connect_id: string;
  name: string;
  url: string;
  is_active: boolean;
}

export type ConnectionType = "kafka" | "registry" | "storage" | "connect";
