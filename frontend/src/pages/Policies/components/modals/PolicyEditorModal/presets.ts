/**
 * Policy Presets
 * Pre-defined templates for common policy configurations
 */

export const NAMING_PRESETS = {
  permissive: {
    name: "Permissive",
    description: "Free format - Startup/Small teams",
    content: `pattern: "^[a-zA-Z0-9._-]+$"
forbidden_prefixes: []
min_length: 1
max_length: 249`,
  },
  balanced: {
    name: "Balanced",
    description: "{env}.{domain}.{resource}[.{action}]",
    content: `pattern: "^(dev|stg|prod)\\.[a-z0-9]+\\.[a-z0-9._-]+$"
forbidden_prefixes:
  - tmp.
  - test.
  - debug.
  - temp.
  - scratch.
allowed_environments:
  - dev
  - stg
  - prod
min_length: 1
max_length: 249`,
  },
  strict: {
    name: "Strict",
    description: "{env}.{classification}.{domain}.{resource}.{version}",
    content: `pattern: "^(dev|stg|prod)\\.(pii|public|internal)\\.[a-z0-9]+\\.[a-z0-9-]+\\.v[0-9]+$"
forbidden_prefixes:
  - tmp.
  - test.
  - debug.
  - temp.
  - scratch.
allowed_environments:
  - dev
  - stg
  - prod
classification_required: true
allowed_classifications:
  - pii
  - public
  - internal
version_required: true
min_length: 1
max_length: 249`,
  },
};

export const GUARDRAIL_PRESETS = {
  dev: {
    name: "DEV",
    description: "Development environment",
    content: `min_insync_replicas: 1
replication_factor: 1
max_partitions: 100
max_retention_ms: 604800000`,
  },
  stg: {
    name: "STG",
    description: "Staging environment",
    content: `min_insync_replicas: 2
replication_factor: 2
max_partitions: 100
max_retention_ms: 2592000000`,
  },
  prod: {
    name: "PROD",
    description: "Production environment",
    content: `min_insync_replicas: 2
replication_factor: 3
max_partitions: 50
max_retention_ms: 7776000000`,
  },
};
