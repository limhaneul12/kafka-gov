# Consumer 모듈 테스트

Consumer 모듈의 단위 테스트 및 통합 테스트

---

## 테스트 구조

```
tests/consumer/
├── __init__.py
├── conftest.py              # Consumer 전용 fixtures
├── test_use_cases.py        # Use Cases 단위 테스트
├── test_delta_builder.py    # Delta Builder 단위 테스트
├── test_repository.py       # Repository 단위 테스트
├── test_websocket.py        # WebSocket 단위 테스트
├── test_integration.py      # 통합 테스트
└── README.md
```

---

## 실행 방법

### 전체 Consumer 테스트 실행

```bash
pytest tests/consumer/ -v
```

### 특정 테스트 파일 실행

```bash
# Use Cases 테스트
pytest tests/consumer/test_use_cases.py -v

# Delta Builder 테스트
pytest tests/consumer/test_delta_builder.py -v

# WebSocket 테스트
pytest tests/consumer/test_websocket.py -v

# 통합 테스트
pytest tests/consumer/test_integration.py -v
```

### 커버리지 포함 실행

```bash
pytest tests/consumer/ --cov=app.consumer --cov-report=html
```

### 특정 테스트 클래스/메서드 실행

```bash
# 특정 클래스
pytest tests/consumer/test_use_cases.py::TestListConsumerGroupsUseCase -v

# 특정 메서드
pytest tests/consumer/test_use_cases.py::TestListConsumerGroupsUseCase::test_execute_returns_groups -v
```

---

## 테스트 커버리지

### Use Cases (`test_use_cases.py`)

- ✅ `ListConsumerGroupsUseCase`
  - 빈 목록 반환
  - 그룹 목록 반환
- ✅ `GetConsumerGroupSummaryUseCase`
  - 그룹 요약 정보 반환
- ✅ `GetGroupMembersUseCase`
  - 멤버와 할당된 파티션 반환
- ✅ `GetGroupPartitionsUseCase`
  - 파티션 목록 반환
- ✅ `GetGroupRebalanceUseCase`
  - 리밸런스 이벤트 조회
- ✅ `GetConsumerGroupMetricsUseCase`
  - 메트릭 정보 반환
- ✅ `GetGroupAdviceUseCase`
  - 정책 어드바이스 반환
- ✅ `GetTopicConsumersUseCase`
  - 토픽별 컨슈머 매핑 반환

### Delta Builder (`test_delta_builder.py`)

- ✅ 델타 계산 (이전 상태 비교)
  - 상태 변경 감지
  - Lag Spike 감지
- ✅ 이벤트 생성
  - `group_state_changed`
  - `lag_spike`
  - `stuck_detected`
  - `assignment_changed`
  - `fairness_warn`
  - `advisor`
  - `system_health`
- ✅ 커스텀 임계치 적용
- ✅ 공통 헤더 검증

### Repository (`test_repository.py`)

- ✅ 최신 그룹 스냅샷 조회
- ✅ 최신 멤버 목록 조회
- ✅ 최신 파티션 목록 조회
- ✅ 토픽별 파티션 조회
- ✅ Stuck 파티션 조회
- ✅ 시간 범위 내 스냅샷 조회
- ✅ Lag 백분위수 계산

### WebSocket (`test_websocket.py`)

- ✅ 엔드포인트 연결 테스트
  - `/ws/consumers/groups/stream`
  - `/ws/consumers/groups/{group_id}`
- ✅ `ConnectionManager`
  - 연결/연결 해제
  - 브로드캐스트
- ✅ `publish_event` 함수
  - 전체 스트림 발행
  - 그룹별 스트림 발행
- ✅ 이벤트 스키마 검증
- ✅ trace_id 고유성 검증
- ✅ 재연결 시나리오

### 통합 테스트 (`test_integration.py`)

- ✅ 전체 플로우: 데이터 저장 → Use Case → 응답
- ✅ 그룹 요약 + 멤버 조회 통합
- ✅ Delta Builder with 실제 데이터
- ✅ WebSocket 이벤트 발행 플로우
- ✅ End-to-End 모니터링 시나리오

---

## Fixtures

### 기본 Fixtures (`tests/conftest.py`)

- `test_engine`: SQLite in-memory 엔진 (세션 스코프)
- `db_session`: 데이터베이스 세션 (함수 스코프, 자동 롤백)
- `clean_db`: 테스트 전후 DB 클린업

### Consumer Fixtures (`tests/consumer/conftest.py`)

- `sample_cluster_id`: 샘플 클러스터 ID
- `sample_group_id`: 샘플 Consumer Group ID
- `sample_timestamp`: 샘플 타임스탬프
- `session_factory`: AsyncSession 팩토리 (Use Cases용)
- `sample_group_snapshot`: 샘플 그룹 스냅샷 (DB 저장됨)
- `sample_group_members`: 샘플 멤버 목록 (3개)
- `sample_group_partitions`: 샘플 파티션 목록 (3개)

---

## 테스트 작성 가이드

### 1. 기본 패턴

```python
import pytest
from app.consumer.application.use_cases.query import ListConsumerGroupsUseCase

class TestMyUseCase:
    @pytest.mark.asyncio
    async def test_something(self, session_factory, sample_cluster_id):
        # Given
        use_case = ListConsumerGroupsUseCase(session_factory)
        
        # When
        result = await use_case.execute(sample_cluster_id)
        
        # Then
        assert result.total == 0
```

### 2. DB 데이터 준비

```python
@pytest.mark.asyncio
async def test_with_data(self, db_session, sample_cluster_id):
    # Given - DB에 데이터 저장
    snapshot = ConsumerGroupSnapshotModel(
        cluster_id=sample_cluster_id,
        group_id="test-group",
        ts=datetime.now(timezone.utc),
        state="Stable",
        # ... 기타 필드
    )
    db_session.add(snapshot)
    await db_session.commit()
    
    # When/Then...
```

### 3. WebSocket 테스트

```python
from fastapi.testclient import TestClient
from app.main import app

def test_websocket_connection():
    client = TestClient(app)
    with client.websocket_connect("/ws/consumers/groups/stream?cluster_id=test") as ws:
        # 테스트 로직
        pass
```

### 4. Mock 사용

```python
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_with_mock():
    with patch('app.consumer.interface.routes.consumer_websocket.manager.broadcast', 
               new_callable=AsyncMock) as mock_broadcast:
        # 테스트 로직
        mock_broadcast.assert_called_once()
```

---

## 주의사항

1. **비동기 테스트**: `@pytest.mark.asyncio` 데코레이터 필수
2. **DB 격리**: 각 테스트는 독립적으로 실행되며 자동 롤백됨
3. **Fixture 의존성**: 필요한 fixture만 파라미터로 받기
4. **타임존**: 모든 datetime은 `timezone.utc` 사용

---

## CI/CD 통합

### GitHub Actions 예시

```yaml
- name: Run Consumer Tests
  run: |
    pytest tests/consumer/ -v --cov=app.consumer --cov-report=xml
    
- name: Upload Coverage
  uses: codecov/codecov-action@v3
  with:
    files: ./coverage.xml
    flags: consumer
```

---

## 트러블슈팅

### 문제: "Database is locked" 에러

**해결**: SQLite는 동시성 제한이 있음. `check_same_thread=False` 설정 확인

### 문제: WebSocket 테스트 실패

**해결**: TestClient의 WebSocket은 실제 연결과 다르게 동작할 수 있음. Mock 사용 고려

### 문제: Fixture가 None

**해결**: 
1. `conftest.py`에 fixture가 정의되어 있는지 확인
2. `@pytest_asyncio.fixture` vs `@pytest.fixture` 구분
3. 스코프 확인 (`scope="session"` vs `scope="function"`)

---

## 다음 단계

- [ ] Repository 메서드 추가 테스트 (백분위수 계산 등)
- [ ] WebSocket 재연결 시나리오 확장
- [ ] 성능 테스트 (부하 테스트)
- [ ] E2E 테스트 (실제 Kafka 연동)
