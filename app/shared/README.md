# 🌐 Shared Module

공통 인프라스트럭처: Database, Event Bus, Exception Handlers

## Structure

```
shared/
├── domain/
│   ├── events.py          # DomainEvent base class
│   ├── models.py          # Common models
│   ├── policy_types.py
│   └── repositories.py    # Repository interfaces
├── infrastructure/
│   ├── event_bus.py       # In-memory async event bus
│   ├── repository.py
│   └── cluster_repository.py
├── application/
│   └── use_cases.py
└── interface/
    └── router.py          # Health check
```

## Key Components

**DomainEvent**: 모든 이벤트의 기본 클래스  
**EventBus**: 모듈 간 이벤트 전파 (Pub-Sub)  
**Database**: SQLAlchemy async session 관리  
**Exception Handlers**: HTTP 에러 처리

## API Endpoints

- `GET /api/health` - Health check
