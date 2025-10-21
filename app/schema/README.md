# 📦 Schema Module

Schema Registry 관리 및 MinIO 아카이빙

## Structure

```
schema/
├── domain/models/          # Schema, CompatibilityMode
├── application/use_cases/  # Upload, Sync, Delete
├── infrastructure/
│   ├── schema_registry_adapter.py
│   └── storage/           # MinIO artifact storage
└── interface/
    ├── router.py
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

- `schema.registered` - 스키마 등록 시 발행 → analysis 모듈이 topic과 연결
