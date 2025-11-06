export type IncidentPolicyStatus = "draft" | "active" | "archived";

export interface IncidentPolicyScope {
  environment: string;
  selector: string;
}

export interface IncidentPolicySchedule {
  mode: "continuous" | "interval" | "window";
  interval: string;
  timezone: string;
  ttl?: string;
  blackout?: string;
  rateLimit: {
    perMinutes: number;
    maxAlerts: number;
  };
}

export interface IncidentPolicyCondition {
  id: string;
  metric: string;
  compareTarget: string;
  operator: string;
  deviation: number;
  baseline: string;
  window: string;
  stat: string;
}

export interface IncidentPolicyResponse {
  slackAlert: boolean;
  enforce: boolean;
  waiver: boolean;
  tags: string[];
  severity: "warn" | "block" | "info";
  memo: string;
}

export interface IncidentPolicyDetail {
  id: string;
  name: string;
  description: string;
  status: IncidentPolicyStatus;
  active: boolean;
  validPeriod: string;
  createdAt: string;
  createdBy: string;
  scope: IncidentPolicyScope;
  schedule: IncidentPolicySchedule;
  rule: {
    logic: "AND" | "OR";
    conditions: IncidentPolicyCondition[];
  };
  response: IncidentPolicyResponse;
}

export const incidentPolicyLibrary: IncidentPolicyDetail[] = [
  {
    id: "INC-001",
    name: "Critical Partition Freeze",
    description: "급격한 파티션 정지 시 트래픽을 안전하게 차단합니다.",
    status: "draft",
    active: false,
    validPeriod: "Continuous · 10m",
    createdAt: "2025-09-22",
    createdBy: "sre.oncall",
    scope: {
      environment: "prod",
      selector: "prod.*",
    },
    schedule: {
      mode: "continuous",
      interval: "10m",
      timezone: "Asia/Seoul",
      ttl: "",
      blackout: "",
      rateLimit: {
        perMinutes: 30,
        maxAlerts: 3,
      },
    },
    rule: {
      logic: "AND",
      conditions: [
        {
          id: "cond-001",
          metric: "growth.rate_1h",
          compareTarget: "baseline",
          operator: "delta_pct",
          deviation: 50,
          baseline: "Rolling p95",
          window: "1h",
          stat: "p95",
        },
        {
          id: "cond-002",
          metric: "isr_ratio",
          compareTarget: "baseline",
          operator: "absolute",
          deviation: 0.7,
          baseline: "Static",
          window: "15m",
          stat: "p95",
        },
      ],
    },
    response: {
      slackAlert: true,
      enforce: true,
      waiver: false,
      tags: ["capacity-anomaly"],
      severity: "warn",
      memo: "핵심 파티션 이상 감지 시 SRE 알림",
    },
  },
  {
    id: "INC-002",
    name: "High Lag Throttle",
    description: "Consumer 지연이 급증할 경우 읽기 트래픽을 줄입니다.",
    status: "active",
    active: true,
    validPeriod: "Interval · 15m",
    createdAt: "2025-10-05",
    createdBy: "platform.ops",
    scope: {
      environment: "prod",
      selector: "analytics-*",
    },
    schedule: {
      mode: "interval",
      interval: "15m",
      timezone: "UTC",
      ttl: "2025-11-06T12:30",
      blackout: "",
      rateLimit: {
        perMinutes: 10,
        maxAlerts: 2,
      },
    },
    rule: {
      logic: "AND",
      conditions: [
        {
          id: "cond-003",
          metric: "consumer.lag.max",
          compareTarget: "previous_interval",
          operator: "delta_pct",
          deviation: 120,
          baseline: "Rolling p90",
          window: "30m",
          stat: "p90",
        },
        {
          id: "cond-004",
          metric: "partition.skew",
          compareTarget: "baseline",
          operator: "absolute",
          deviation: 25,
          baseline: "Static",
          window: "6h",
          stat: "p95",
        },
      ],
    },
    response: {
      slackAlert: true,
      enforce: false,
      waiver: true,
      tags: ["lag", "throughput"],
      severity: "warn",
      memo: "대시보드에서 승인 후 throttle 적용",
    },
  },
  {
    id: "INC-003",
    name: "Retention Policy Watch",
    description: "Retention 설정이 기준 이하로 떨어지지 않도록 감시합니다.",
    status: "archived",
    active: false,
    validPeriod: "Continuous · 1h",
    createdAt: "2025-09-18",
    createdBy: "qa.lead",
    scope: {
      environment: "stage",
      selector: "stage-*",
    },
    schedule: {
      mode: "continuous",
      interval: "1h",
      timezone: "Asia/Seoul",
      ttl: "",
      blackout: "",
      rateLimit: {
        perMinutes: 5,
        maxAlerts: 1,
      },
    },
    rule: {
      logic: "OR",
      conditions: [
        {
          id: "cond-005",
          metric: "topic.retention.ms",
          compareTarget: "baseline",
          operator: "absolute",
          deviation: 86400000,
          baseline: "Static",
          window: "24h",
          stat: "p95",
        },
      ],
    },
    response: {
      slackAlert: false,
      enforce: false,
      waiver: false,
      tags: ["retention"],
      severity: "info",
      memo: "stage 환경 감시용",
    },
  },
];

export function getIncidentPolicyById(id: string) {
  return incidentPolicyLibrary.find((policy) => policy.id === id);
}
