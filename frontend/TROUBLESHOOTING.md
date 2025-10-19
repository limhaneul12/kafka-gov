# 프론트엔드 연결 문제 해결 가이드

## 문제: 버튼을 눌러도 반응이 없음

### 1단계: 백엔드 상태 확인

```bash
# Docker 컨테이너 상태 확인
docker ps | grep kafka-gov

# 백엔드 로그 확인
docker logs kafka-gov-app-1 --tail 50

# 백엔드 헬스 체크
curl http://localhost:8000/health
curl http://localhost:8000/api
```

예상 응답:
```json
{"status":"healthy"}
{"message":"Kafka Governance API","version":"1.0.0"}
```

### 2단계: 프론트엔드 실행

```bash
cd frontend

# 의존성 설치 (처음 한 번만)
npm install

# 개발 서버 시작
npm run dev
```

프론트엔드는 **http://localhost:3000**에서 실행됩니다.

### 3단계: 브라우저에서 연결 테스트

1. http://localhost:3000 접속
2. Dashboard 페이지에서 **"연결 테스트"** 버튼 클릭
3. 브라우저 개발자 도구(F12) > Console 탭에서 로그 확인

#### 성공 시:
```
✅ API Connection OK: {message: "Kafka Governance API", version: "1.0.0"}
```

#### 실패 시 확인 사항:

**케이스 1: Network Error / CORS Error**
- 백엔드가 실행 중인지 확인: `docker ps`
- 포트 8000이 열려있는지 확인: `curl http://localhost:8000/health`

**케이스 2: 404 Not Found**
- API 경로 확인
- Vite 프록시 설정 확인 (vite.config.ts)

**케이스 3: 500 Internal Server Error**
- 백엔드 로그 확인: `docker logs kafka-gov-app-1 --tail 50`

### 4단계: Vite 프록시 설정 확인

`frontend/vite.config.ts`:
```typescript
server: {
  port: 3000,
  proxy: {
    '/api': {
      target: 'http://localhost:8000',
      changeOrigin: true,
    },
  },
}
```

### 5단계: 네트워크 디버깅

브라우저 개발자 도구 > Network 탭에서:
1. API 요청이 전송되는지 확인
2. 요청 URL: `http://localhost:3000/api/...`
3. 응답 상태 코드 확인
4. 응답 헤더의 CORS 설정 확인

### 일반적인 해결 방법

#### 백엔드가 응답하지 않는 경우:
```bash
# Docker 컨테이너 재시작
docker-compose down
docker-compose up -d

# 로그 확인
docker logs -f kafka-gov-app-1
```

#### 프론트엔드가 백엔드를 찾지 못하는 경우:
```bash
# 프론트엔드 개발 서버 재시작
cd frontend
npm run dev
```

#### 포트 충돌:
```bash
# 8000번 포트 사용 중인 프로세스 확인
lsof -i :8000

# 3000번 포트 사용 중인 프로세스 확인
lsof -i :3000
```

## 추가 디버깅 팁

### 1. API 직접 호출 테스트
```bash
# Clusters 조회
curl http://localhost:8000/api/v1/clusters/kafka

# Statistics 조회
curl http://localhost:8000/api/v1/analysis/statistics
```

### 2. 브라우저 콘솔에서 직접 테스트
```javascript
// 개발자 도구 Console에서 실행
fetch('/api/')
  .then(r => r.json())
  .then(d => console.log('✅ Success:', d))
  .catch(e => console.error('❌ Error:', e))
```

### 3. React DevTools로 컴포넌트 상태 확인
- React DevTools 설치
- 컴포넌트 state 확인 (loading, error, data 등)

## 연락처
문제가 계속되면 다음 정보를 함께 제공해주세요:
1. `docker ps` 출력
2. `docker logs kafka-gov-app-1 --tail 50` 출력
3. 브라우저 Console 에러 메시지
4. 브라우저 Network 탭 스크린샷
