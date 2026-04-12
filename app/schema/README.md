# 📦 Schema Module

Schema Registry 관리, MinIO 아카이빙, 그리고 naming-derived known topic-name hints 제공.

## Structure

```
schema/
├── domain/models/          # Schema, CompatibilityMode
├── application/use_cases/  # Upload, Sync, Delete
├── infrastructure/
│   ├── schema_registry_adapter.py
│   └── storage/           # MinIO artifact storage
└── interface/
    ├── routers/
    └── schemas/
```

## Compatibility Modes

- **BACKWARD**: 신규 스키마가 구 데이터 읽기 가능
- **FORWARD**: 구 스키마가 신규 데이터 읽기 가능
- **FULL**: BACKWARD + FORWARD
- **NONE**: 검증 없음

## API Endpoints

**Schema Operations** (`/api/v1/schemas`):  
- `GET /` - List schemas (`?cluster_id=`)
- `POST /upload` - Upload schema
- `POST /sync` - Sync from Schema Registry
- `GET /artifacts` - List MinIO artifacts
- `DELETE /{subject}` - Delete schema

## Domain Events

- `schema.registered` - 스키마 등록 시 발행 → shared audit/approval handlers가 후속 처리를 수행
