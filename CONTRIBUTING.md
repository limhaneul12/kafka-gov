# 🤝 기여 가이드 (Contributing Guide)

Kafka-Gov 프로젝트에 기여해주셔서 감사합니다! 이 문서는 프로젝트에 기여하는 방법과 코드 작성 규칙을 안내합니다.

---

## 📋 목차

- [시작하기](#-시작하기)
- [개발 환경 설정](#-개발-환경-설정)
- [코드 스타일 및 규칙](#-코드-스타일-및-규칙)
- [커밋 컨벤션](#-커밋-컨벤션)
- [테스트 작성](#-테스트-작성)
- [Pull Request 프로세스](#-pull-request-프로세스)
- [아키텍처 가이드](#-아키텍처-가이드)
- [문의하기](#-문의하기)

---

## 🚀 시작하기

### 1. 저장소 Fork 및 Clone

```bash
# Fork the repository on GitHub
# Then clone your fork
git clone https://github.com/YOUR_USERNAME/kafka-gov.git
cd kafka-gov

# Add upstream remote
git remote add upstream https://github.com/limhaneul12/kafka-gov.git
```

### 2. 브랜치 생성

```bash
# 최신 코드로 업데이트
git checkout main
git pull upstream main

# 기능 브랜치 생성
git checkout -b feature/your-feature-name
# 또는 버그 수정 브랜치
git checkout -b fix/your-bugfix-name
```

**브랜치 네이밍 컨벤션:**
- `feature/` - 새로운 기능 추가
- `fix/` - 버그 수정
- `docs/` - 문서 수정
- `refactor/` - 코드 리팩토링
- `test/` - 테스트 추가/수정
- `chore/` - 빌드 설정, 의존성 업데이트 등

---

## 🛠️ 개발 환경 설정

### 필수 요구사항

- **Python**: 3.12 이상
- **uv**: Python 패키지 매니저 (초고속 의존성 해결)
- **Docker & Docker Compose**: 로컬 Kafka/Schema Registry 실행용
- **MySQL**: 8.0 이상 (또는 Docker Compose 사용)

### uv 설치

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 개발 환경 구축

```bash
# 1. Python 가상환경 생성 및 의존성 설치
uv sync

# 2. Pre-commit hooks 설치
uv run pre-commit install

# 3. 환경 변수 설정
cp .env.example .env
# .env 파일을 열어 Kafka/DB 연결 정보 수정

# 4. 암호화 키 생성 (민감한 정보 암호화용)
uv run python generate_encryption_key.py

# 5. Docker Compose로 Kafka/Schema Registry 실행
docker-compose up -d

# 6. 데이터베이스 마이그레이션
uv run alembic upgrade head

# 7. 애플리케이션 실행
uv run uvicorn app.main:app --reload
```

**애플리케이션 접속:**
- Web UI: http://localhost:8000
- API Docs: http://localhost:8000/swagger
- Health Check: http://localhost:8000/health

---

## 📏 코드 스타일 및 규칙

### 기본 원칙

프로젝트는 **Python 3.12+**를 기준으로 하며, 다음 원칙을 준수합니다:

1. **타입 안정성**: 모든 함수/클래스는 엄격한 타입 힌트 사용
2. **경계 분리**: IO 경계(Pydantic)와 내부 도메인(msgspec) 명확히 구분
3. **검증 최소화**: 입력 시 1회 검증만 수행, 내부에서 중복 검증 금지
4. **테스트 우선**: pytest 기반 단위 테스트 우선 작성
5. **의존성 관리**: uv로 관리하며 불필요한 라이브러리 추가 금지

### 타입 힌트 규칙

```python
# ✅ 올바른 예시 (Python 3.12+ 네이티브 문법)
def process_data(items: list[str], config: dict[str, int]) -> str | None:
    """데이터 처리 함수"""
    ...

# ❌ 잘못된 예시 (구식 문법)
from typing import Optional, List, Dict

def process_data(items: List[str], config: Dict[str, int]) -> Optional[str]:
    ...
```

**타입 힌트 표준:**
- `list[T]` 사용 (❌ `List[T]`)
- `dict[K, V]` 사용 (❌ `Dict[K, V]`)
- `str | None` 사용 (❌ `Optional[str]`)
- `tuple[T, ...]` 사용 (❌ `Tuple[T, ...]`)

### 데이터 모델 규칙

**IO 경계 (외부 입출력)**
```python
from pydantic import BaseModel, Field

class CreateTopicRequest(BaseModel):
    """API 요청 모델 - 런타임 검증 필요"""
    name: str = Field(..., pattern=r'^[a-z0-9\-\.]+$')
    partitions: int = Field(..., ge=1)
    replication_factor: int = Field(..., ge=1)
```

**내부 도메인 (비즈니스 로직)**
```python
import msgspec

class Topic(msgspec.Struct, frozen=True):
    """도메인 모델 - 불변 구조체"""
    name: str
    partitions: int
    replication_factor: int
    created_at: datetime
```

### 지연 로딩 금지

```python
# ❌ 절대 금지
def process():
    from app.shared.domain.events import DomainEvent  # 함수 내부 import 금지
    ...

# ✅ 올바른 방법
from app.shared.domain.events import DomainEvent

def process():
    ...
```

### 코드 포맷팅 및 린팅

프로젝트는 **Ruff**를 사용하여 자동 포맷팅 및 린팅을 수행합니다.

```bash
# 코드 포맷팅
uv run ruff format .

# 린팅 (자동 수정 가능한 항목)
uv run ruff check --fix .

# 린팅 (수정 없이 검사만)
uv run ruff check .
```

**Pre-commit hook이 자동으로 실행됩니다:**
- 커밋 시 자동으로 Ruff 포맷팅 및 린팅 실행
- 위반 사항이 있으면 커밋 실패 → 수정 후 재시도

---

## 📝 커밋 컨벤션

### Conventional Commits 형식

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Type:**
- `feat`: 새로운 기능 추가
- `fix`: 버그 수정
- `docs`: 문서 수정
- `style`: 코드 포맷팅 (기능 변경 없음)
- `refactor`: 코드 리팩토링
- `test`: 테스트 추가/수정
- `chore`: 빌드 설정, 의존성 업데이트 등
- `perf`: 성능 개선

**Scope (선택사항):**
- `topic`, `schema`, `connect`, `cluster`, `analysis`, `shared`

### 예시

```bash
# 기능 추가
git commit -m "feat(connect): Add connector pause/resume endpoints"

# 버그 수정
git commit -m "fix(schema): Fix compatibility check validation"

# 문서 업데이트
git commit -m "docs: Update API reference for Connect endpoints"

# 리팩토링
git commit -m "refactor(topic): Extract validation logic to domain service"
```

---

## 🧪 테스트 작성

### 테스트 원칙

1. **단위 테스트 우선**: 도메인 로직은 반드시 단위 테스트 작성
2. **80% 이상 커버리지**: 새로운 코드는 최소 80% 테스트 커버리지 유지
3. **Fixture 활용**: pytest fixture로 테스트 데이터 재사용
4. **비동기 테스트**: `pytest-asyncio` 사용

### 테스트 실행

```bash
# 전체 테스트 실행
uv run pytest

# 커버리지 포함
uv run pytest --cov=app --cov-report=html

# 특정 모듈만 테스트
uv run pytest tests/connect/

# 특정 테스트 파일만
uv run pytest tests/connect/test_connector_service.py

# 실패한 테스트만 재실행
uv run pytest --lf

# 병렬 실행 (속도 향상)
uv run pytest -n auto
```

### 테스트 작성 예시

```python
# tests/connect/test_connector_service.py
import pytest
from app.connect.application.services import ConnectorService
from app.connect.domain.models import ConnectorInfo, ConnectorType, ConnectorState

@pytest.fixture
def mock_connector_info():
    """테스트용 커넥터 정보 fixture"""
    return ConnectorInfo(
        name="test-connector",
        type=ConnectorType.SOURCE,
        state=ConnectorState.RUNNING,
        worker_id="worker-1",
        config={"connector.class": "io.debezium.connector.mysql.MySqlConnector"},
        tasks=[],
        topics=["test.topic"],
    )

@pytest.mark.asyncio
async def test_get_connector_info(connector_service: ConnectorService, mock_connector_info):
    """커넥터 정보 조회 테스트"""
    # Given
    connector_name = "test-connector"
    
    # When
    result = await connector_service.get_connector(connector_name)
    
    # Then
    assert result.name == connector_name
    assert result.type == ConnectorType.SOURCE
    assert result.state == ConnectorState.RUNNING
```

---

## 🔄 Pull Request 프로세스

### 1. PR 생성 전 체크리스트

- [ ] 모든 테스트 통과 (`uv run pytest`)
- [ ] 코드 커버리지 80% 이상 유지
- [ ] Ruff 포맷팅 및 린팅 통과
- [ ] 타입 힌트 누락 없음
- [ ] 문서 업데이트 (API 변경 시)
- [ ] 커밋 메시지가 컨벤션 준수

### 2. PR 생성

```bash
# 브랜치 푸시
git push origin feature/your-feature-name

# GitHub에서 Pull Request 생성
```

### 3. PR 설명 템플릿

```markdown
## 📋 변경 사항

<!-- 무엇을 변경했는지 간략히 설명 -->

## 🎯 변경 이유

<!-- 왜 이 변경이 필요한지 설명 -->

## 🧪 테스트 방법

<!-- 어떻게 테스트했는지 설명 -->

## 📸 스크린샷 (선택사항)

<!-- UI 변경이 있다면 스크린샷 첨부 -->

## ✅ 체크리스트

- [ ] 테스트 작성 완료
- [ ] 문서 업데이트 완료
- [ ] 코드 리뷰 준비 완료
```

### 4. 코드 리뷰 대응

- 리뷰어의 피드백에 정중하게 응답
- 요청된 변경사항을 반영하고 커밋 추가
- 토론이 필요한 부분은 PR 코멘트로 논의

### 5. Merge 조건

- **최소 1명의 Approve** 필요
- **모든 CI 테스트 통과**
- **Conflict 없음**

---

## 🏗️ 아키텍처 가이드

### Clean Architecture 레이어

프로젝트는 Clean Architecture 원칙을 따릅니다:

```
app/
├── [domain]/
│   ├── domain/              # 도메인 모델 (비즈니스 규칙)
│   │   ├── models.py       # msgspec 불변 구조체
│   │   ├── repositories.py # 저장소 인터페이스 (ABC)
│   │   ├── services.py     # 도메인 서비스
│   │   └── events.py       # 도메인 이벤트
│   │
│   ├── application/         # 유스케이스 (애플리케이션 로직)
│   │   ├── use_cases.py    # 유스케이스 구현
│   │   ├── dtos.py         # DTO (Pydantic)
│   │   └── mappers.py      # DTO ↔ Domain 변환
│   │
│   ├── infrastructure/      # 외부 어댑터 (DB, API 클라이언트)
│   │   ├── models.py       # SQLAlchemy 모델
│   │   ├── repositories.py # 저장소 구현체
│   │   └── client.py       # 외부 API 클라이언트
│   │
│   └── interface/           # 인터페이스 어댑터 (API 라우터)
│       └── router.py        # FastAPI 라우터
```

### 의존성 방향

```
Interface → Application → Domain ← Infrastructure
```

- **Domain**: 의존성 없음 (순수 비즈니스 로직)
- **Application**: Domain에만 의존
- **Infrastructure**: Domain 인터페이스 구현
- **Interface**: Application 호출

### 새로운 기능 추가 예시

**1. Domain 모델 정의**
```python
# app/connect/domain/models.py
import msgspec

class Connector(msgspec.Struct, frozen=True):
    """커넥터 도메인 모델"""
    name: str
    type: ConnectorType
    state: ConnectorState
    config: dict[str, str]
```

**2. Repository 인터페이스**
```python
# app/connect/domain/repositories.py
from abc import ABC, abstractmethod

class ConnectorRepository(ABC):
    """커넥터 저장소 인터페이스"""
    
    @abstractmethod
    async def find_by_name(self, name: str) -> Connector | None:
        ...
```

**3. Repository 구현**
```python
# app/connect/infrastructure/repositories.py
class ConnectorRepositoryImpl(ConnectorRepository):
    """커넥터 저장소 구현체"""
    
    async def find_by_name(self, name: str) -> Connector | None:
        # SQLAlchemy로 DB 조회
        ...
```

**4. UseCase 작성**
```python
# app/connect/application/use_cases.py
class GetConnectorUseCase:
    """커넥터 조회 유스케이스"""
    
    def __init__(self, repository: ConnectorRepository):
        self.repository = repository
    
    async def execute(self, name: str) -> ConnectorDTO:
        connector = await self.repository.find_by_name(name)
        if not connector:
            raise ConnectorNotFoundError(name)
        return ConnectorMapper.to_dto(connector)
```

**5. API 라우터 추가**
```python
# app/connect/interface/router.py
@router.get("/connectors/{name}")
async def get_connector(
    name: str,
    use_case: GetConnectorUseCase = Depends(Provide[...])
):
    return await use_case.execute(name)
```

---

## 🎨 도메인 이벤트 사용

### 이벤트 발행

```python
# 도메인 이벤트 정의
class ConnectorCreatedEvent(DomainEvent):
    connector_name: str
    connector_type: ConnectorType

# 이벤트 발행
from app.shared.domain.event_bus import EventBus

await event_bus.publish(ConnectorCreatedEvent(
    connector_name="my-connector",
    connector_type=ConnectorType.SOURCE
))
```

### 이벤트 구독

```python
# 이벤트 핸들러 등록
@event_bus.subscribe(ConnectorCreatedEvent)
async def on_connector_created(event: ConnectorCreatedEvent):
    logger.info(f"Connector created: {event.connector_name}")
    # 후속 작업 (예: 토픽 자동 생성)
```

---

## 📚 참고 자료

- [Clean Architecture](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [Python 3.12 문서](https://docs.python.org/3.12/)
- [FastAPI 문서](https://fastapi.tiangolo.com/)
- [Confluent Kafka Python](https://docs.confluent.io/kafka-clients/python/current/overview.html)
- [pytest 문서](https://docs.pytest.org/)
- [Conventional Commits](https://www.conventionalcommits.org/)

---

## 💬 문의하기

질문이나 제안사항이 있다면:

1. **GitHub Issues**: 버그 리포트, 기능 제안
2. **GitHub Discussions**: 일반적인 질문, 아이디어 공유
3. **Pull Request**: 직접 기여

---

## 🙏 감사합니다!

여러분의 기여가 Kafka-Gov를 더 나은 프로젝트로 만듭니다. 🎉

**Happy coding!** 🚀
