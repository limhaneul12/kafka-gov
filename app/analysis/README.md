# 🔗 Analysis Module

Topic-Schema 자동 연결 및 영향도 분석

## Structure

```
analysis/
├── domain/models.py        # TopicSchemaLink
├── application/
│   ├── queries.py         # Read queries
│   └── event_handlers.py  # topic.created, schema.registered 구독
└── interface/router.py
```

## Event Handlers

**SchemaRegisteredHandler**: 스키마 등록 시 매칭되는 토픽 자동 연결  
**TopicCreatedHandler**: 토픽 생성 시 매칭되는 스키마 자동 연결

## Correlation Rules

- **Exact Match**: `{topic}-value`, `{topic}-key`
- **Confidence**: 1.0 (exact) ~ 0.7 (fuzzy)

## API Endpoints

**Analysis** (`/api/v1/analysis`):  
- `GET /correlation/by-topic/{topic}` - 토픽이 사용하는 스키마
- `GET /correlation/by-schema/{subject}` - 스키마를 사용하는 토픽
- `GET /impact/schema/{subject}` - 스키마 변경 영향도 분석
