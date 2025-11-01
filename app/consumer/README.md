# 👥 Consumer Module

Real-time consumer group monitoring and governance insights

## Structure

```
consumer/
├── domain/
│   ├── models/              # ConsumerGroup, Member, Partition
│   ├── services/            # Lag, Rebalance, Fairness analysis
│   ├── thresholds.py        # SLO/SLA threshold definitions
│   ├── types_enum.py        # State, Assignor types
│   └── value_objects.py     # LagMetrics, PartitionAssignment
├── application/
│   ├── services/            # Consumer health, snapshot services
│   └── use_cases/
│       ├── query.py         # Consumer group queries
│       ├── topic_detail.py  # Topic + Consumer Health integration
│       ├── metrics.py       # Lag, Fairness, Rebalance metrics
│       ├── list_groups.py   # Consumer group list
│       ├── topic_stats.py   # Topic statistics
│       └── collect_snapshot.py  # Snapshot collection
├── infrastructure/
│   ├── kafka_consumer_repository.py  # AdminClient-based queries
│   └── snapshot_repository.py        # PostgreSQL snapshot storage
└── interface/
    ├── routes/
    │   ├── consumer_routes.py   # REST API
    │   └── websocket_routes.py  # Real-time monitoring
    └── schema/                  # Pydantic schemas
```

## Core Features

### 📊 Consumer Group Monitoring
- **State Tracking**: Stable, Rebalancing, Empty, Dead
- **Member Info**: Client ID, Host, Partition assignments
- **Lag Metrics**: P50, P95, Max, Total
- **Assignor**: Range, RoundRobin, Sticky, CooperativeSticky

### 🎯 Governance Insights
- **SLO Compliance**: Calculate target SLA compliance rate (default: 95%)
- **Stuck Partition Detection**: Detect partitions with increasing lag over specified time
- **Rebalance Score**: Rebalance stability score (0-100)
- **Fairness Index**: Measure partition distribution fairness using Gini coefficient (0=perfectly fair, 1=unfair)

### 🚨 Real-time Alerts
- **SLO Violation**: Alerts for SLO compliance failures
- **Stuck Partitions**: Notifications for partitions with continuously increasing lag
- **Rebalance Instability**: Warnings for frequent rebalance occurrences
- **Unfair Distribution**: Detection of unfair partition distribution

### 📈 Topic-Level Analysis
- **Consumer Health Summary**: Health status of all Consumer Groups consuming the topic
- **Coverage**: Ratio of consumed partitions to total partitions
- **Aggregated Metrics**: Average SLO, total stuck partitions, overall status summary

## API Endpoints

### Consumer Group Operations (`/api/v1/consumers`)

**REST API**:
- `GET /groups` - List consumer groups (`?cluster_id=`)
- `GET /groups/{group_id}` - Get consumer group details (`?cluster_id=`)
- `GET /groups/{group_id}/health` - Get health metrics (Lag, SLO, Fairness)
- `GET /topics/{topic_name}/consumers` - List consumer groups consuming the topic
- `GET /topics/{topic_name}/detail` - Topic + Consumer Health integrated view

**WebSocket**:
- `WS /ws/consumers/groups/{group_id}/live` - Real-time monitoring
  - Query params: `cluster_id`, `interval` (seconds)
  - Periodically streams Lag, State, Member information

## Domain Models

### ConsumerGroup
```python
@dataclass
class ConsumerGroup:
    cluster_id: str
    group_id: str
    state: ConsumerGroupState  # Stable, Rebalancing, Empty, Dead
    members: list[ConsumerMember]
    partition_assignor: str
    topics: list[str]
```

### LagMetrics
```python
@dataclass
class LagMetrics:
    lag_p50: int      # Median lag
    lag_p95: int      # 95th percentile lag
    lag_max: int      # Maximum lag
    total_lag: int    # Sum of all lags
```

### ConsumerHealthSummary
```python
@dataclass
class ConsumerHealthSummary:
    group_id: str
    state: str
    slo_compliance: float         # 0.0 ~ 1.0
    rebalance_score: float | None # 0 ~ 100
    fairness_gini: float          # 0.0 ~ 1.0
    stuck_count: int
    recommendation: str | None
```

## Metrics Calculation

### SLO Compliance
```python
# Ratio of partitions where Lag P95 < threshold
slo_compliance = (partitions_under_threshold / total_partitions) * 100
```

### Fairness Index (Gini Coefficient)
```python
# 0 = perfectly fair, 1 = completely unfair
# Calculated from partition count distribution per member
gini = calculate_gini(partition_counts_per_member)
```

### Rebalance Score
```python
# Based on rebalance history from recent N snapshots
# Stable = 100, Frequent rebalances = 0
score = 100 - (rebalance_count / max_rebalances * 100)
```

## Thresholds (Configurable)

```python
SLO_THRESHOLD_P95_LAG = 1000        # P95 Lag threshold (ms)
SLO_COMPLIANCE_MIN = 0.95           # Minimum SLO compliance rate
REBALANCE_SCORE_MIN = 70            # Minimum rebalance score
FAIRNESS_GINI_MAX = 0.3             # Maximum Gini coefficient
STUCK_DETECTION_WINDOW = 5 * 60     # Stuck detection window (seconds)
```

## Use Cases

### 1. Topic Detail with Consumer Health
Query topic details and health of all Consumer Groups consuming the topic in an integrated view

```python
use_case = GetTopicDetailWithConsumerHealthUseCase(...)
result = await use_case.execute(cluster_id, topic_name)
# → TopicDetailWithConsumerHealthResponse
```

**Response**:
- Topic info (partitions, replication, retention)
- Consumer health list (SLO, Lag, Fairness for each group)
- Governance alerts (SLO violations, Stuck partitions, etc.)
- Insight summary (Overall status summary)

### 2. Real-time Live Monitoring
Real-time Consumer Group monitoring via WebSocket

```python
# WebSocket: /ws/consumers/groups/{group_id}/live?cluster_id=X&interval=10
# Automatically sends latest status every 10 seconds
```

### 3. Consumer Group List
Query list of all Consumer Groups in a cluster (with Lag statistics)

```python
use_case = ListConsumerGroupsUseCase(...)
groups = await use_case.execute(cluster_id)
# → List[ConsumerGroupWithLagResponse]
```

## Integration Points

### With Topic Module
- Display Consumer Health on Topic detail pages
- Analyze Consumer Group impact when creating/deleting Topics

### With Analysis Module
- Consumer lag trend analysis
- Consumer Group statistics by Team

### With Snapshot
- Periodic snapshot collection (Lag, Rebalance history)
- Rebalance Score calculation based on time-series data

## Event-Driven Architecture

**Domain Events** (future expansion):
- `consumer.rebalanced` - When rebalance occurs
- `consumer.lag_spike` - When lag spikes
- `consumer.slo_violated` - When SLO is violated

## Frontend Integration

### Dashboard
- Consumer Groups card: Total group count, distribution by state (Stable/Rebalancing/Other)
- Total Lag metric

### Topic Detail Page
- 📊 Governance Insights: Overall Consumer Health summary
- 🚨 Governance Alerts: Real-time alert list
- 👥 Consumer Groups Health: Detailed metrics for each group

### Consumer List Page
- Consumer Group list
- Lag statistics (P50, P95, Max, Total)
- State, Members, Topics

### WebSocket Monitoring
- Real-time Lag chart
- Member change detection
- State change notifications

## Testing

```bash
# Unit tests
pytest tests/consumer/

# Specific tests
pytest tests/consumer/test_metrics.py
pytest tests/consumer/test_topic_detail.py
```

## Performance Considerations

- **Lag Calculation**: Uses Kafka AdminClient's `list_consumer_group_offsets()`
- **Batch Queries**: Query multiple Consumer Groups at once to minimize API calls
- **Caching**: Optimize repeated queries with short TTL (5-10 seconds)
- **WebSocket**: Adjust polling frequency based on client-specified interval

## Roadmap

- [ ] Historical lag trend chart
- [ ] Consumer Group creation/deletion
- [ ] Partition reassignment UI
- [ ] Lag alert threshold per topic
- [ ] Auto-scaling recommendation based on lag
- [ ] Consumer Group ACL management
