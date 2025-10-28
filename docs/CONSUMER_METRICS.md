# 📊 Consumer Group Metrics & Calculation Guide

Complete reference for all consumer group metrics, formulas, and detection algorithms used in Kafka-Gov.

---

## 📑 Table of Contents

1. [Lag Statistics](#1-lag-statistics)
2. [Fairness Index (Gini Coefficient)](#2-fairness-index-gini-coefficient)
3. [Rebalance Stability Score](#3-rebalance-stability-score)
4. [Stuck Partition Detection](#4-stuck-partition-detection)
5. [Governance Metrics](#5-governance-metrics)
6. [Thresholds Configuration](#6-thresholds-configuration)

---

## 1. Lag Statistics

### 1.1 Basic Lag Calculation

**Per-Partition Lag:**
```
lag_i = latest_offset_i - committed_offset_i
```

Where:
- `latest_offset_i`: High water mark of partition i (producer side)
- `committed_offset_i`: Last committed offset by consumer group
- If `lag_i < 0`: Clamp to 0 (edge case: topic deletion/recreation)

### 1.2 Aggregate Lag Metrics

**Total Lag:**
```
total_lag = Σ(lag_i) for all partitions
```

**Mean Lag:**
```
mean_lag = total_lag / N
```
Where `N` = number of partitions with valid lag

**Percentile Calculation (Linear Interpolation):**

For p-th percentile (e.g., p=0.50 for median, p=0.95 for 95th):

```python
def percentile(sorted_lags: list[int], p: float) -> int:
    """
    Calculate p-th percentile using linear interpolation.
    
    Args:
        sorted_lags: Sorted list of lag values
        p: Percentile (0.0 to 1.0)
    
    Returns:
        Interpolated percentile value
    """
    if not sorted_lags:
        return 0
    
    k = (len(sorted_lags) - 1) * p
    f = int(k)  # floor
    c = f + 1   # ceiling
    
    if c >= len(sorted_lags):
        return sorted_lags[-1]
    
    # Linear interpolation
    d0 = sorted_lags[f] * (c - k)
    d1 = sorted_lags[c] * (k - f)
    return int(d0 + d1)
```

**Example:**
```
Partitions: [p0: 100, p1: 250, p2: 450, p3: 800, p4: 1200]

total_lag = 100 + 250 + 450 + 800 + 1200 = 2800
mean_lag  = 2800 / 5 = 560
p50_lag   = 450  (median)
p95_lag   = 1120 (interpolated between 800 and 1200)
max_lag   = 1200
```

### 1.3 Implementation Reference

**Location:** `app/consumer/domain/services/collector.py::ConsumerDataCollector._calculate_lag_stats()`

**Response Schema:**
```json
{
  "total_lag": 2800,
  "mean_lag": 560.0,
  "p50_lag": 450,
  "p95_lag": 1120,
  "max_lag": 1200,
  "partition_count": 5
}
```

---

## 2. Fairness Index (Gini Coefficient)

### 2.1 Definition

Measures how evenly partitions are distributed among consumer group members. Lower is better.

**Gini Coefficient Formula:**
```
G = Σ|x_i - x_j| / (2n² * μ)
```

Where:
- `x_i`: Number of partitions assigned to member i
- `n`: Total number of members
- `μ`: Mean partitions per member = total_partitions / n

### 2.2 Simplified Implementation

```python
def gini_coefficient(assignments: list[int]) -> float:
    """
    Calculate Gini coefficient for partition distribution.
    
    Args:
        assignments: List of partition counts per member
                    e.g., [3, 5, 4, 4] means 4 members with different partition counts
    
    Returns:
        Gini coefficient (0.0 = perfect equality, 1.0 = maximum inequality)
    """
    if not assignments or len(assignments) == 1:
        return 0.0
    
    n = len(assignments)
    mean = sum(assignments) / n
    
    if mean == 0:
        return 0.0
    
    # Sum of absolute differences
    total_diff = sum(
        abs(x_i - x_j)
        for x_i in assignments
        for x_j in assignments
    )
    
    return total_diff / (2 * n * n * mean)
```

### 2.3 Interpretation

| Gini Value | Interpretation | Action |
|------------|----------------|--------|
| 0.0 - 0.20 | Excellent balance | ✅ No action needed |
| 0.20 - 0.40 | Good balance | ✅ Monitor |
| 0.40 - 0.60 | Moderate imbalance | ⚠️ Consider rebalancing |
| 0.60+ | Poor balance | 🚨 **Immediate action** - Check assignor strategy |

### 2.4 Example Calculation

**Scenario:** 4 members, 16 partitions

**Case A: Perfect Balance**
```
Members: [4, 4, 4, 4]
Mean = 4
Gini = 0.0  ✅ Perfect
```

**Case B: Slight Imbalance**
```
Members: [3, 4, 5, 4]
Mean = 4
Total_diff = |3-4| + |3-5| + |3-4| + |4-3| + |4-5| + ... = 16
Gini = 16 / (2 * 4² * 4) = 16 / 128 = 0.125  ✅ Good
```

**Case C: Severe Imbalance**
```
Members: [1, 2, 3, 10]
Mean = 4
Total_diff = 72
Gini = 72 / 128 = 0.5625  🚨 Poor balance!
```

### 2.5 Implementation Reference

**Location:** `app/consumer/domain/services/calculator.py::ConsumerMetricsCalculator.calculate_fairness()`

**Response Schema:**
```json
{
  "gini_coefficient": 0.125,
  "interpretation": "good_balance",
  "member_partition_distribution": {
    "consumer-1": 3,
    "consumer-2": 4,
    "consumer-3": 5,
    "consumer-4": 4
  }
}
```

---

## 3. Rebalance Stability Score

### 3.1 Definition

Measures how stable a consumer group is over time based on rebalance frequency and partition movement.

### 3.2 Calculation Components

**A. Rebalance Rate (per hour):**
```
rebalance_rate = rebalances_count / time_window_hours
```

**B. Movement Ratio:**
```
movement_ratio = avg_moved_partitions / total_partitions
```

**C. Stability Ratio:**
```
stability_ratio = stable_time / total_time
```

Where:
- `stable_time`: Duration in "Stable" state
- `total_time`: Total observation window

### 3.3 Combined Rebalance Score

```python
def rebalance_score(
    rebalances: int,
    avg_moved_partitions: float,
    total_partitions: int,
    stable_ratio: float,
    window_hours: int = 1
) -> float:
    """
    Calculate rebalance stability score (0-100).
    
    Higher score = more stable (fewer rebalances, less movement)
    
    Args:
        rebalances: Number of rebalance events in window
        avg_moved_partitions: Average partitions moved per rebalance
        total_partitions: Total number of partitions
        stable_ratio: Ratio of time in Stable state (0.0-1.0)
        window_hours: Time window in hours
    
    Returns:
        Score from 0 (very unstable) to 100 (perfectly stable)
    """
    # Component 1: Frequency penalty (0-40 points)
    # Penalize high rebalance rate
    rate = rebalances / window_hours
    rate_threshold = 4.0  # More than 4/hour is concerning
    frequency_score = max(0, 40 * (1 - rate / rate_threshold))
    
    # Component 2: Movement penalty (0-30 points)
    # Penalize high movement ratio
    movement_ratio = avg_moved_partitions / max(total_partitions, 1)
    movement_threshold = 0.10  # 10% movement is threshold
    movement_score = max(0, 30 * (1 - movement_ratio / movement_threshold))
    
    # Component 3: Stability bonus (0-30 points)
    # Reward high stable time ratio
    stability_score = 30 * stable_ratio
    
    return frequency_score + movement_score + stability_score
```

### 3.4 Interpretation

| Score | Interpretation | Typical Cause |
|-------|----------------|---------------|
| 90-100 | Excellent stability | Stable group, no issues |
| 70-89 | Good stability | Occasional rebalances |
| 50-69 | Moderate stability | Frequent member churn or auto-scaling |
| 30-49 | Poor stability | Deployment cycles, unstable members |
| 0-29 | Critical instability | ⚠️ Investigate immediately |

### 3.5 Example Calculation

**Scenario:** 1-hour window, 12 partitions

**Case A: Stable Group**
```
rebalances = 1
avg_moved = 4
stable_ratio = 0.95

frequency_score = 40 * (1 - 1/4) = 30
movement_score = 30 * (1 - (4/12)/0.10) = 20
stability_score = 30 * 0.95 = 28.5

Total Score = 30 + 20 + 28.5 = 78.5  ✅ Good
```

**Case B: Unstable Group**
```
rebalances = 8
avg_moved = 10
stable_ratio = 0.30

frequency_score = 40 * (1 - 8/4) = 0 (clamped)
movement_score = 30 * (1 - (10/12)/0.10) = 0 (clamped)
stability_score = 30 * 0.30 = 9

Total Score = 0 + 0 + 9 = 9  🚨 Critical!
```

### 3.6 Implementation Reference

**Location:** `app/consumer/domain/models/rebalance.py::RebalanceRollup.rebalance_score()`

**Database Rollup:** Aggregated per time window (1h, 24h) in `consumer_group_rebalance_rollup` table

---

## 4. Stuck Partition Detection

### 4.1 Definition

A partition is "stuck" when:
1. Consumer is **not advancing** committed offset (Δcommitted ≤ ε)
2. **AND** lag is **growing** (Δlag > θ)
3. **AND** condition persists for **minimum duration** (≥ T_min)

This indicates a **silent failure** where the consumer appears healthy but isn't processing.

### 4.2 Detection Algorithm

```python
def is_stuck(
    current: ConsumerPartition,
    previous: ConsumerPartition,
    epsilon: int = 1,     # Max allowed committed delta
    theta: int = 10       # Min required lag growth
) -> bool:
    """
    Detect if partition is stuck.
    
    Args:
        current: Current partition state
        previous: Previous partition state (typically 3 minutes ago)
        epsilon: Threshold for committed offset change
        theta: Threshold for lag increase
    
    Returns:
        True if partition meets stuck criteria
    """
    if previous is None:
        return False
    
    # Extract offsets with None handling
    curr_committed = current.committed_offset or 0
    prev_committed = previous.committed_offset or 0
    curr_lag = current.lag or 0
    prev_lag = previous.lag or 0
    
    # Calculate deltas
    delta_committed = curr_committed - prev_committed
    delta_lag = curr_lag - prev_lag
    
    # Check stuck conditions
    return delta_committed <= epsilon and delta_lag > theta
```

### 4.3 Time-Based Filtering

Only report partitions stuck for **minimum duration**:

```python
def detect_stuck_partitions(
    current_partitions: list[ConsumerPartition],
    previous_partitions: list[ConsumerPartition],
    min_duration_seconds: int = 180  # 3 minutes default
) -> list[StuckPartition]:
    """
    Detect stuck partitions with duration filtering.
    
    Maintains state across multiple checks to track duration.
    """
    stuck_results = []
    
    for current in current_partitions:
        previous = find_matching_partition(current, previous_partitions)
        
        if is_stuck(current, previous):
            duration = (current.ts - previous.ts).total_seconds()
            
            if duration >= min_duration_seconds:
                stuck_results.append(
                    StuckPartition(
                        topic=current.topic,
                        partition=current.partition,
                        assigned_member_id=current.assigned_member_id,
                        since_ts=previous.ts,
                        current_lag=current.lag,
                        delta_committed=curr_committed - prev_committed,
                        delta_lag=curr_lag - prev_lag
                    )
                )
    
    return stuck_results
```

### 4.4 Default Thresholds

Configured in `app/consumer/domain/thresholds.py`:

```python
@dataclass(frozen=True, slots=True)
class StuckThresholds:
    """Stuck Partition Detection Thresholds"""
    
    delta_committed_le: int = 1     # Committed change ≤ 1
    delta_lag_ge: int = 10          # Lag growth ≥ 10
    duration_s_ge: int = 180        # Must persist ≥ 3 minutes
```

### 4.5 Example Scenarios

**Scenario A: Healthy Partition**
```
t0: committed=1000, lag=50
t1: committed=1050, lag=45

Δcommitted = 50  > 1   ✅ Processing
Δlag = -5            ✅ Catching up
Result: NOT stuck
```

**Scenario B: Stuck Partition**
```
t0: committed=1000, lag=50
t1: committed=1000, lag=75

Δcommitted = 0   ≤ 1   🚨 No progress
Δlag = 25        > 10  🚨 Lag growing
Duration: 3+ min       🚨 Persistent
Result: STUCK ⚠️
```

**Scenario C: Slow Consumer (Not Stuck)**
```
t0: committed=1000, lag=50
t1: committed=1020, lag=70

Δcommitted = 20  > 1   ✅ Still processing
Δlag = 20        > 10  ⚠️ Falling behind
Result: NOT stuck (just slow)
```

### 4.6 Response Format

```json
{
  "stuck": [
    {
      "topic": "orders-topic",
      "partition": 7,
      "assigned_member_id": "consumer-3",
      "since_ts": "2025-10-28T10:15:00Z",
      "current_lag": 15234,
      "delta_committed": 0,
      "delta_lag": 45
    }
  ]
}
```

### 4.7 Implementation Reference

**Location:** 
- Detection Logic: `app/consumer/domain/services/detector.py::StuckPartitionDetector`
- Use Case: `app/consumer/application/use_cases/query.py::GetConsumerGroupSummaryUseCase._get_stuck_partitions()`

---

## 5. Governance Metrics

### 5.1 SLO Compliance

**Definition:** Percentage of time consumer group meets its Service Level Objective for lag.

```python
def calculate_slo_compliance(
    lag_history: list[tuple[datetime, int]],
    slo_threshold: int,
    time_window_hours: int = 24
) -> float:
    """
    Calculate SLO compliance percentage.
    
    Args:
        lag_history: List of (timestamp, lag) tuples
        slo_threshold: Maximum acceptable lag
        time_window_hours: Evaluation window
    
    Returns:
        Compliance percentage (0.0 to 1.0)
    """
    if not lag_history:
        return 1.0
    
    compliant_samples = sum(1 for _, lag in lag_history if lag <= slo_threshold)
    total_samples = len(lag_history)
    
    return compliant_samples / total_samples
```

**Example:**
```
SLO: Lag must be ≤ 1000
24h history: 1440 samples (1 per minute)
Compliant: 1380 samples
Non-compliant: 60 samples

SLO Compliance = 1380 / 1440 = 95.8%  ✅
```

### 5.2 Policy Recommendations

**Assignor Strategy:**
```python
def recommend_assignor(
    gini: float,
    member_count: int,
    total_partitions: int
) -> str:
    """
    Recommend partition assignor based on metrics.
    
    Returns:
        "Range" | "RoundRobin" | "Sticky" | "CooperativeSticky"
    """
    if gini > 0.40:
        # High imbalance → Use RoundRobin
        return "RoundRobin"
    
    if member_count > 10 and total_partitions > 50:
        # Large group → Use CooperativeSticky for incremental rebalancing
        return "CooperativeSticky"
    
    # Default for most cases
    return "Sticky"
```

**Scaling Recommendation:**
```python
def recommend_scale(
    max_lag: int,
    p95_lag: int,
    member_count: int,
    total_partitions: int
) -> str:
    """
    Recommend scaling action.
    
    Returns:
        "scale_up" | "scale_down" | "ok"
    """
    if max_lag > 10000 or p95_lag > 5000:
        if member_count < total_partitions:
            return "scale_up"  # Underutilized partitions
    
    if max_lag < 100 and p95_lag < 50:
        if member_count > total_partitions / 2:
            return "scale_down"  # Over-provisioned
    
    return "ok"
```

### 5.3 Risk ETA (Estimated Time to Violation)

**Linear Extrapolation:**
```python
def estimate_slo_violation_eta(
    current_lag: int,
    lag_growth_rate: float,  # per minute
    slo_threshold: int
) -> datetime | None:
    """
    Predict when lag will exceed SLO threshold.
    
    Args:
        current_lag: Current lag value
        lag_growth_rate: Rate of lag increase (calculated from recent history)
        slo_threshold: SLO lag limit
    
    Returns:
        Estimated datetime of violation, or None if not trending to violation
    """
    if lag_growth_rate <= 0:
        return None  # Lag is stable or decreasing
    
    if current_lag >= slo_threshold:
        return datetime.now(UTC)  # Already violated
    
    minutes_to_violation = (slo_threshold - current_lag) / lag_growth_rate
    return datetime.now(UTC) + timedelta(minutes=minutes_to_violation)
```

**Example:**
```
Current lag: 800
Growth rate: 50/min (observed over last 10 minutes)
SLO threshold: 2000

ETA = (2000 - 800) / 50 = 24 minutes from now
```

---

## 6. Thresholds Configuration

All thresholds are configurable via `app/consumer/domain/thresholds.py`:

```python
@dataclass(frozen=True, slots=True)
class ConsumerThresholds:
    """Centralized threshold configuration"""
    
    lag: LagThresholds = field(default_factory=LagThresholds)
    stuck: StuckThresholds = field(default_factory=StuckThresholds)
    rebalance: RebalanceThresholds = field(default_factory=RebalanceThresholds)
    fairness: FairnessThresholds = field(default_factory=FairnessThresholds)
```

### 6.1 Lag Thresholds

```python
class LagThresholds:
    spike_delta_total_lag: int = 2000  # Detect lag spikes > 2000 in 60s
    spike_window_s: int = 60           # Detection window
```

### 6.2 Stuck Thresholds

```python
class StuckThresholds:
    delta_committed_le: int = 1        # Committed offset change ≤ 1
    delta_lag_ge: int = 10             # Lag growth ≥ 10
    duration_s_ge: int = 180           # Minimum duration: 3 minutes
```

### 6.3 Rebalance Thresholds

```python
class RebalanceThresholds:
    rate_warn_per_hour: int = 4        # Warn if > 4 rebalances/hour
    movement_rate_warn: float = 0.10   # Warn if > 10% partitions moved
```

### 6.4 Fairness Thresholds

```python
class FairnessThresholds:
    gini_warn: float = 0.40            # Warn if Gini > 0.40
```

### 6.5 Runtime Override

Thresholds can be overridden at runtime:

```python
from app.consumer.domain.thresholds import ConsumerThresholds, StuckThresholds

custom_thresholds = ConsumerThresholds(
    stuck=StuckThresholds(
        delta_committed_le=0,     # Stricter: no movement allowed
        delta_lag_ge=5,           # Lower threshold
        duration_s_ge=300         # Longer duration: 5 minutes
    )
)

detector = StuckPartitionDetector(
    epsilon=custom_thresholds.stuck.delta_committed_le,
    theta=custom_thresholds.stuck.delta_lag_ge,
    min_duration_seconds=custom_thresholds.stuck.duration_s_ge
)
```

---

## 📚 References

### Domain Models
- **ConsumerGroup**: `app/consumer/domain/models/consumer.py`
- **ConsumerPartition**: `app/consumer/domain/models/partition.py`
- **StuckPartition**: `app/consumer/domain/models/partition.py`
- **RebalanceRollup**: `app/consumer/domain/models/rebalance.py`

### Services
- **ConsumerDataCollector**: `app/consumer/domain/services/collector.py`
- **ConsumerMetricsCalculator**: `app/consumer/domain/services/calculator.py`
- **StuckPartitionDetector**: `app/consumer/domain/services/detector.py`

### Use Cases
- **GetConsumerGroupSummaryUseCase**: `app/consumer/application/use_cases/query.py`
- **GetConsumerGroupMetricsUseCase**: `app/consumer/application/use_cases/metrics.py`

### Infrastructure
- **Database Models**: `app/consumer/infrastructure/models.py`
- **Repository**: `app/consumer/infrastructure/repository/consumer_repository.py`

---

## 🔗 Related Documentation

- [Consumer Module README](../app/consumer/README.md)
- [Main README](../README.md)
- [Architecture Overview](../CONTRIBUTING.md)

---

**Last Updated:** October 28, 2025  
**Version:** 1.0.0
