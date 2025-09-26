# Kafka Governance API

Kafka Topic 및 Schema Registry 관리를 위한 Clean Architecture 기반 API 서비스입니다.

## 🏗️ 아키텍처

이 프로젝트는 Clean Architecture 원칙을 따라 도메인별로 구조화되어 있습니다:

```
app/
├── shared/                    # 공통 모듈
│   ├── settings.py           # Pydantic Settings 기반 설정 (공통 helper로 일관화)
│   └── containers.py         # 공통 인프라 컨테이너 + 모듈 컨테이너 집합 초기화
├── topic/                    # Topic 도메인
│   ├── containers.py         # Topic 모듈 DI 컨테이너
│   ├── domain/              # 도메인 레이어
│   │   ├── models.py        # 도메인 모델
│   │   ├── repositories.py  # 리포지토리 인터페이스
│   │   └── services.py      # 도메인 서비스
│   ├── application/         # 애플리케이션 레이어
│   │   └── services.py      # 유스케이스 조정
│   ├── infrastructure/      # 인프라 레이어
│   │   └── repositories.py  # 리포지토리 구현
│   └── interface/           # 인터페이스 레이어
│       ├── router.py        # FastAPI 라우터
│       └── schemas.py       # API 스키마
├── schema/                  # Schema Registry 도메인
│   ├── containers.py        # Schema 모듈 DI 컨테이너
│   └── (동일한 구조)
├── auth/                    # 인증 도메인 (신규)
│   ├── containers.py        # Auth 모듈 DI 컨테이너
│   ├── domain/              # 도메인 레이어
│   ├── application/         # 애플리케이션 서비스
│   ├── infrastructure/      # 인프라(인메모리 저장소)
│   └── interface/           # 라우터
└── main.py                  # 애플리케이션 엔트리포인트
```

## 🚀 주요 기능

### Topic 관리
- Topic 생성, 수정, 삭제
- 배치 작업 계획 수립 및 실행
- 정책 검증 및 위반 사항 확인
- Dry-run 모드 지원

### Schema Registry 관리
- 스키마 등록, 조회, 삭제
- Subject 및 버전 관리
- 호환성 모드 설정
- MinIO 기반 스키마 저장소

## 🛠️ 기술 스택

- **Framework**: FastAPI
- **DI Container**: dependency-injector
- **Settings**: pydantic-settings
- **Database**: SQLAlchemy (Async)
- **Kafka**: confluent-kafka-python
- **Storage**: MinIO
- **Type Safety**: Python 3.12+ with strict typing
- **Auth**: argon2-cffi (패스워드 해시), python-jose (JWT)

## 📋 환경 설정

1. `.env` 파일을 생성하고 `.env.example`을 참고하여 설정:

```bash
cp .env.example .env
```

2. 주요 설정 항목:
   - `KAFKA_BOOTSTRAP_SERVERS`: Kafka 브로커 서버 목록
   - `MINIO_ENDPOINT`: MinIO 서버 엔드포인트
   - `SCHEMA_REGISTRY_URL`: Schema Registry URL
   - `DATABASE_URL`: 데이터베이스 연결 URL
   - `SECRET_KEY`: JWT 서명용 시크릿 (예시값 제공, 반드시 교체)
   - `JWT_ALGORITHM`, `JWT_EXPIRE_MINUTES`: JWT 설정

## 🏃‍♂️ 실행 방법

### 개발 환경

```bash
# 의존성 설치
pip install -r requirements.txt

# 개발 서버 실행
python -m app.main
```

### Docker Compose 실행

```bash
docker-compose up -d
```

## 📚 API 문서

서버 실행 후 다음 URL에서 API 문서를 확인할 수 있습니다:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 🧪 주요 엔드포인트

### Topic 관리
- `GET /api/v1/topics/{env}` - Topic 목록 조회
- `GET /api/v1/topics/{env}/{topic_name}` - Topic 설정 조회
- `POST /api/v1/topics/{env}/plan` - 배치 작업 계획 수립
- `POST /api/v1/topics/{env}/apply` - 배치 작업 실행

### Schema Registry
- `GET /api/v1/schemas/subjects` - Subject 목록 조회
- `GET /api/v1/schemas/subjects/{subject}/versions` - Subject 버전 목록
- `GET /api/v1/schemas/subjects/{subject}/versions/{version}` - 스키마 조회
- `POST /api/v1/schemas/{env}/plan` - 스키마 배치 계획 수립
- `POST /api/v1/schemas/{env}/apply` - 스키마 배치 실행

### Auth (신규)
- `POST /api/v1/auth/register` - 회원가입 및 액세스 토큰 발급
- `POST /api/v1/auth/login` - 로그인 및 액세스 토큰 발급

응답:
```
{
  "access_token": "...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

## 🔧 개발 원칙

### 타입 안정성
- Python 3.12+ 기준 엄격한 타입 힌트 사용
- `Optional` 대신 `| None` 사용
- 모든 공개 함수/클래스에 타입 힌트 필수

### 도메인 분리
- IO 경계는 Pydantic 모델 사용
- 내부 도메인은 dataclass(frozen=True, slots=True) 사용
- 불변성 원칙 준수

### 의존성 관리
- dependency-injector 기반
- 공통 인프라 컨테이너(shared) + 모듈별 컨테이너(topic/schema/auth) 구성
- 모듈 경계에서만 와이어링(lifespan에서 초기화)

## 🏥 헬스체크

```bash
curl http://localhost:8000/health
```

## 📝 라이선스

MIT License