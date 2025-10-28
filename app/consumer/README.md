# 👥 Consumer Module

실시간 컨슈머 그룹 모니터링 및 거버넌스 인사이트

## Structure

```
consumer/
├── domain/
│   ├── models/              # ConsumerGroup, Member, Partition
│   ├── services/            # Lag, Rebalance, Fairness 분석
│   ├── thresholds.py        # SLO/SLA 임계값 정의
│   ├── types_enum.py        # State, Assignor 타입
│   └── value_objects.py     # LagMetrics, PartitionAssignment
├── application/
│   ├── services/            # Consumer health, snapshot 서비스
│   └── use_cases/
│       ├── query.py         # Consumer group 조회
│       ├── topic_detail.py  # Topic + Consumer Health 통합
│       ├── metrics.py       # Lag, Fairness, Rebalance 메트릭
│       ├── list_groups.py   # Consumer group 목록
│       ├── topic_stats.py   # Topic 통계
│       └── collect_snapshot.py  # Snapshot 수집
├── infrastructure/
│   ├── kafka_consumer_repository.py  # AdminClient 기반 조회
│   └── snapshot_repository.py        # PostgreSQL 스냅샷 저장
└── interface/
    ├── routes/
    │   ├── consumer_routes.py   # REST API
    │   └── websocket_routes.py  # 실시간 모니터링
    └── schema/                  # Pydantic 스키마
```

## Core Features

### 📊 Consumer Group Monitoring
- **State Tracking**: Stable, Rebalancing, Empty, Dead
- **Member Info**: Client ID, Host, 파티션 할당
- **Lag Metrics**: P50, P95, Max, Total
- **Assignor**: Range, RoundRobin, Sticky, CooperativeSticky

### 🎯 Governance Insights
- **SLO Compliance**: 목표 SLA 준수율 계산 (기본: 95%)
- **Stuck Partition Detection**: 지정 시간 동안 Lag 증가하는 파티션 감지
- **Rebalance Score**: 리밸런스 안정성 점수 (0-100)
- **Fairness Index**: Gini 계수로 파티션 분배 공정성 측정 (0=완전공정, 1=불공정)

### 🚨 Real-time Alerts
- **SLO Violation**: SLO 준수율 미달 경고
- **Stuck Partitions**: Lag이 지속 증가하는 파티션 알림
- **Rebalance Instability**: 빈번한 리밸런스 발생 경고
- **Unfair Distribution**: 불공정한 파티션 분배 감지

### 📈 Topic-Level Analysis
- **Consumer Health Summary**: 토픽을 소비하는 모든 Consumer Group의 헬스 상태
- **Coverage**: 전체 파티션 중 소비되는 파티션 비율
- **Aggregated Metrics**: 평균 SLO, 총 Stuck 파티션, 전체 상태 요약

## API Endpoints

### Consumer Group Operations (`/api/v1/consumers`)

**REST API**:
- `GET /groups` - Consumer group 목록 조회 (`?cluster_id=`)
- `GET /groups/{group_id}` - Consumer group 상세 (`?cluster_id=`)
- `GET /groups/{group_id}/health` - Health 메트릭 (Lag, SLO, Fairness)
- `GET /topics/{topic_name}/consumers` - 토픽을 소비하는 Consumer group 목록
- `GET /topics/{topic_name}/detail` - Topic + Consumer Health 통합 뷰

**WebSocket**:
- `WS /ws/consumers/groups/{group_id}/live` - 실시간 모니터링
  - Query params: `cluster_id`, `interval` (초)
  - 주기적으로 Lag, State, Member 정보 스트리밍

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
# Lag P95 < threshold인 파티션 비율
slo_compliance = (partitions_under_threshold / total_partitions) * 100
```

### Fairness Index (Gini Coefficient)
```python
# 0 = 완전 공정, 1 = 완전 불공정
# 각 멤버의 파티션 할당 개수 분포로 계산
gini = calculate_gini(partition_counts_per_member)
```

### Rebalance Score
```python
# 최근 N개 스냅샷의 리밸런스 이력 기반
# 안정적 = 100, 빈번한 리밸런스 = 0
score = 100 - (rebalance_count / max_rebalances * 100)
```

## Thresholds (Configurable)

```python
SLO_THRESHOLD_P95_LAG = 1000        # P95 Lag 임계값 (ms)
SLO_COMPLIANCE_MIN = 0.95           # 최소 SLO 준수율
REBALANCE_SCORE_MIN = 70            # 최소 리밸런스 점수
FAIRNESS_GINI_MAX = 0.3             # 최대 Gini 계수
STUCK_DETECTION_WINDOW = 5 * 60     # Stuck 감지 시간 (초)
```

## Use Cases

### 1. Topic Detail with Consumer Health
토픽 상세 정보와 해당 토픽을 소비하는 모든 Consumer Group의 Health를 통합 조회

```python
use_case = GetTopicDetailWithConsumerHealthUseCase(...)
result = await use_case.execute(cluster_id, topic_name)
# → TopicDetailWithConsumerHealthResponse
```

**Response**:
- Topic info (partitions, replication, retention)
- Consumer health list (각 group의 SLO, Lag, Fairness)
- Governance alerts (SLO 미달, Stuck 파티션 등)
- Insight summary (전체 상태 요약)

### 2. Real-time Live Monitoring
WebSocket을 통한 실시간 Consumer Group 모니터링

```python
# WebSocket: /ws/consumers/groups/{group_id}/live?cluster_id=X&interval=10
# 10초마다 자동으로 최신 상태 전송
```

### 3. Consumer Group List
클러스터의 모든 Consumer Group 목록 조회 (Lag 통계 포함)

```python
use_case = ListConsumerGroupsUseCase(...)
groups = await use_case.execute(cluster_id)
# → List[ConsumerGroupWithLagResponse]
```

## Integration Points

### With Topic Module
- Topic 상세 페이지에서 Consumer Health 표시
- Topic 생성/삭제 시 Consumer Group 영향 분석

### With Analysis Module
- Consumer lag 추세 분석
- Team별 Consumer Group 통계

### With Snapshot
- 주기적 스냅샷 수집 (Lag, Rebalance 이력)
- 시계열 데이터 기반 Rebalance Score 계산

## Event-Driven Architecture

**Domain Events** (향후 확장):
- `consumer.rebalanced` - 리밸런스 발생 시
- `consumer.lag_spike` - Lag 급증 시
- `consumer.slo_violated` - SLO 위반 시

## Frontend Integration

### Dashboard
- Consumer Groups 카드: 총 그룹 수, Stable/Rebalancing/Other 상태별 분포
- Total Lag 메트릭

### Topic Detail Page
- 📊 Governance Insights: 전체 Consumer Health 요약
- 🚨 Governance Alerts: 실시간 경고 목록
- 👥 Consumer Groups Health: 각 그룹의 상세 메트릭

### Consumer List Page
- Consumer Group 목록
- Lag 통계 (P50, P95, Max, Total)
- State, Members, Topics

### WebSocket Monitoring
- 실시간 Lag 차트
- Member 변경 감지
- State 변화 알림

## Testing

```bash
# 단위 테스트
pytest tests/consumer/

# 특정 테스트
pytest tests/consumer/test_metrics.py
pytest tests/consumer/test_topic_detail.py
```

## Performance Considerations

- **Lag 계산**: Kafka AdminClient의 `list_consumer_group_offsets()` 사용
- **Batch 조회**: 여러 Consumer Group을 한 번에 조회하여 API 호출 최소화
- **Caching**: 짧은 TTL (5-10초)로 반복 조회 최적화
- **WebSocket**: 클라이언트가 지정한 interval로 polling 빈도 조절

## Roadmap

- [ ] Historical lag trend chart
- [ ] Consumer Group creation/deletion
- [ ] Partition reassignment UI
- [ ] Lag alert threshold per topic
- [ ] Auto-scaling recommendation based on lag
- [ ] Consumer Group ACL management
