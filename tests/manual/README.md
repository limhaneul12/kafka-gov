# 🧪 Manual Test Consumers

Topic Detail 페이지 테스트를 위한 Consumer Group 생성

## 📦 구성

- **Consumer Group**: `addition-calculator-group`
- **Topic**: `addition`
- **Consumer 3개**:
  - `addition-consumer-1` (빠름: 0.1s/msg)
  - `addition-consumer-2` (보통: 0.15s/msg)
  - `addition-consumer-3` (느림: 0.5s/msg) ← lag 생성용

## 🚀 실행 방법

### 1. Topic 생성

먼저 Kafka-Gov UI에서 `addition` 토픽을 생성하거나, CLI로 생성:

```bash
# Option A: Kafka-Gov UI
# Topics → Create Topic → Name: "addition", Partitions: 6

# Option B: Kafka CLI
kafka-topics --create \
  --topic addition \
  --partitions 6 \
  --replication-factor 1 \
  --bootstrap-server kafka1:19092
```

### 2. Consumer 실행 (터미널 1개) ✨

**하나의 스크립트에서 3개 Consumer 동시 실행 (멀티스레드):**

```bash
uv run python tests/manual/test_consumer_1.py
```

이 스크립트가 자동으로 3개의 Consumer를 스레드로 실행합니다:
- `addition-consumer-1` (빠름: 0.1s)
- `addition-consumer-2` (보통: 0.15s)
- `addition-consumer-3` (느림: 0.5s)

### 3. Producer 실행 (터미널 2)

```bash
uv run python tests/manual/test_producer.py
```

Producer가 메시지를 생성하면, 3개의 Consumer가 파티션을 분할하여 소비합니다.

## 📊 예상 결과

### Kafka-Gov UI에서 확인:

**1. Consumer List 페이지 (`/consumers`)**
```
addition-calculator-group
├── State: Stable
├── Members: 3
├── Lag: ~500-1000 (Consumer 3 때문에)
└── Topics: 1 (addition)
```

**2. Consumer Detail 페이지 (`/consumers/addition-calculator-group`)**
```
Members:
- addition-consumer-1 → Partitions [0, 3]
- addition-consumer-2 → Partitions [1, 4]
- addition-consumer-3 → Partitions [2, 5] (lag 많음)

Metrics:
- Fairness Gini: ~0.0 (균등 분배)
- Rebalance Score: 80-90 (안정적)
- SLO Compliance: 80-90% (Consumer 3 때문에 낮음)
```

**3. Topic Detail 페이지 (`/topics/addition`) 🔥**
```
Topic: addition
├── Partitions: 6
├── Replication: 1
└── Retention: 7d

Consumer Insight:
├── Total Consumers: 1
├── Healthy: 0-1 (Consumer 3 때문에)
├── Unhealthy: 0-1
├── Avg SLO: 80-90%
├── Stuck Partitions: 0 (정상)
└── Summary: "⚠️ 1개 Consumer Group이 SLO 미달"

Consumer Groups:
✅ addition-calculator-group
   ├── SLO: 85% (Consumer 3 영향)
   ├── P95 Lag: 800-1200
   ├── Stuck: 0
   ├── Rebalance Score: 85/100
   └── Recommendation: "Scale-out 필요"
```

## 🎯 테스트 시나리오

### Scenario 1: 정상 운영
```bash
# Producer: 초당 10개 메시지
# Consumer 1, 2, 3 모두 실행
# 예상: Consumer 3가 lag 발생, SLO 80-90%
```

### Scenario 2: Stuck Partition 시뮬레이션
```bash
# Consumer 3를 Ctrl+C로 중지
# Producer 계속 실행
# 예상: Consumer 3의 파티션들이 Stuck 감지
```

### Scenario 3: Rebalance 시뮬레이션
```bash
# Consumer 3 중지 → Rebalance 발생
# Consumer 1, 2가 파티션 재분배
# 다시 Consumer 3 시작 → 또 Rebalance
# 예상: Rebalance Score 하락
```

### Scenario 4: Scale-out 테스트
```bash
# Consumer 4개로 늘리기
# 예상: 파티션당 Consumer 비율 개선, Lag 감소
```

## 🔍 Consumer 특징

| Consumer | 처리 속도 | 역할 | 예상 Lag |
|----------|-----------|------|----------|
| Consumer 1 | 빠름 (0.1s) | 기준선 | 낮음 (~50-100) |
| Consumer 2 | 보통 (0.15s) | 평균 | 보통 (~100-200) |
| Consumer 3 | 느림 (0.5s) | Lag 생성 | 높음 (~500-1000) |

## 📝 메시지 포맷

```json
{
  "id": 1,
  "a": 42,
  "b": 17,
  "timestamp": 1730122800.123
}
```

각 Consumer는 `a + b`를 계산하고 출력합니다.

## 🛑 정리

```bash
# 모든 터미널에서 Ctrl+C
# (Consumer와 Producer 모두 종료)

# Topic 삭제 (필요시)
kafka-topics --delete --topic addition --bootstrap-server localhost:9092
```

## 💡 Tips

- **Lag 증가**: Producer 속도를 높이거나 (`time.sleep(0.05)`)
- **Stuck 생성**: Consumer 1개를 강제 종료
- **Rebalance**: Consumer를 추가/제거
- **Fairness 테스트**: 파티션 수를 조정 (3, 6, 9)

---

**테스트 완료 후 Topic Detail 페이지에서 Consumer Health를 확인하세요!** 🎉
