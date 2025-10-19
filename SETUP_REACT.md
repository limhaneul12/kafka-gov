# React 프론트엔드 설정 가이드

## ✅ 완료된 작업

### 1. 프로젝트 구조
```
frontend/
├── src/
│   ├── components/
│   │   ├── layout/
│   │   │   ├── Sidebar.tsx       # 사이드바 네비게이션
│   │   │   ├── Header.tsx        # 헤더
│   │   │   └── Layout.tsx        # 메인 레이아웃
│   │   └── ui/
│   │       ├── Button.tsx        # 버튼 컴포넌트
│   │       ├── Card.tsx          # 카드 컴포넌트
│   │       ├── Badge.tsx         # 뱃지 컴포넌트
│   │       └── Loading.tsx       # 로딩 스피너
│   ├── pages/
│   │   ├── Dashboard.tsx         # 대시보드
│   │   ├── Topics.tsx            # 토픽 관리
│   │   ├── Schemas.tsx           # 스키마 관리
│   │   ├── Connect.tsx           # Kafka Connect
│   │   ├── Connections.tsx       # 연결 관리
│   │   ├── Policies.tsx          # 정책 관리
│   │   ├── Analysis.tsx          # 분석
│   │   └── Settings.tsx          # 설정
│   ├── services/
│   │   └── api.ts                # API 클라이언트
│   ├── types/
│   │   └── index.ts              # TypeScript 타입 정의
│   ├── utils/
│   │   └── cn.ts                 # 유틸리티 함수
│   ├── App.tsx                   # 메인 앱
│   ├── main.tsx                  # 진입점
│   └── index.css                 # 글로벌 스타일
├── package.json
├── tailwind.config.js
├── postcss.config.js
└── vite.config.ts
```

### 2. 기술 스택
- ⚛️ **React 19** - UI 라이브러리
- 📘 **TypeScript** - 타입 안정성
- ⚡ **Vite** - 빌드 도구
- 🎨 **TailwindCSS** - 스타일링
- 🔀 **React Router v7** - 라우팅
- 🔌 **Axios** - HTTP 클라이언트
- 🎭 **Lucide React** - 아이콘

### 3. 구현된 기능
- ✅ 사이드바 네비게이션 대시보드 레이아웃
- ✅ 7개 페이지 구현 (Dashboard, Topics, Schemas, Connect, Connections, Policies, Analysis)
- ✅ 재사용 가능한 UI 컴포넌트
- ✅ FastAPI 백엔드와 연동되는 API 서비스
- ✅ TypeScript 타입 정의
- ✅ Vite 프록시 설정 (개발 환경)

## 🚀 설치 및 실행

### 1. 의존성 설치
```bash
cd frontend
npm install
```

### 2. 개발 서버 실행
```bash
# 프론트엔드 개발 서버 (포트 3000)
npm run dev
```

프론트엔드는 http://localhost:3000 에서 실행되며,
`/api/*` 요청은 자동으로 http://localhost:8000 (FastAPI)로 프록시됩니다.

### 3. 백엔드 실행 (별도 터미널)
```bash
# 프로젝트 루트에서
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. 프로덕션 빌드
```bash
cd frontend
npm run build
```

빌드된 파일은 `frontend/dist`에 생성되며, FastAPI가 정적 파일로 서빙합니다.

## 📁 API 엔드포인트

프론트엔드는 다음 백엔드 API를 사용합니다:

- `GET /api/v1/topics` - 토픽 목록
- `GET /api/v1/schemas/artifacts` - 스키마 목록
- `GET /api/v1/clusters/kafka` - Kafka 클러스터 목록
- `GET /api/v1/clusters/schema-registries` - Schema Registry 목록
- `GET /api/v1/clusters/storages` - Object Storage 목록
- `GET /api/v1/policies` - 정책 목록
- `GET /api/v1/analysis/statistics` - 통계
- `GET /api/v1/analysis/correlations` - 토픽-스키마 상관관계

## 🎨 디자인 시스템

### 색상 팔레트
- **Primary**: Blue-600 (#0284c7)
- **Success**: Green-600
- **Warning**: Yellow-600
- **Danger**: Red-600
- **Gray**: Gray-50 ~ Gray-900

### 컴포넌트
- **Button**: primary, secondary, danger, ghost 변형
- **Badge**: default, success, warning, danger, info 변형
- **Card**: Header, Title, Content 구조

## 📝 다음 단계

### 기능 추가
1. **토픽 생성/삭제 모달** 구현
2. **스키마 업로드** 폼 구현
3. **Kafka Connect 커넥터** 관리 UI
4. **정책 편집기** (JSON/YAML)
5. **실시간 모니터링** 대시보드
6. **검색 필터** 고도화

### 개선 사항
1. **에러 처리** 개선 (Toast 알림)
2. **로딩 상태** UX 개선
3. **테이블 페이지네이션**
4. **다크 모드** 지원
5. **반응형 디자인** 모바일 대응

## 🐛 알려진 이슈

현재 TypeScript/ESLint 경고들은 `npm install` 후 해결됩니다:
- `react-router-dom` 모듈 미설치
- `lucide-react` 모듈 미설치
- 기타 타입 경고들

## 📚 참고 문서

- [React Router v7](https://reactrouter.com/)
- [TailwindCSS](https://tailwindcss.com/)
- [Lucide Icons](https://lucide.dev/)
- [Vite](https://vitejs.dev/)
