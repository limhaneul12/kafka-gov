# 🎯 Topic Module

토픽 생명주기 관리: 배치 생성/수정/삭제, 메타데이터, 정책 검증

## Structure

```
topic/
├── domain/
│   ├── models/          # DomainTopicSpec, DomainTopicPlan, Report
│   ├── policies/        # naming/, guardrail/, management/, validation/
│   ├── repositories/    # Abstract interfaces
│   └── services.py
├── application/use_cases/
│   ├── batch_dry_run.py
│   ├── batch_apply.py
│   ├── batch_apply_yaml.py
│   ├── bulk_delete.py
│   └── list_topics.py
├── infrastructure/
│   ├── kafka_adapter.py
│   └── repository/      # DB implementations
└── interface/
    ├── router.py        # Batch operations
    ├── policy_router.py
    └── schemas/
```

## Key Models

**DomainTopicSpec**: 토픽 생성/수정 스펙  
**DomainTopicPlan**: Dry-run 실행 계획  
**DryRunReport**: 검증 결과 리포트

## Naming Policies

| Strategy | Pattern |
| **Permissive** | Free-form |
| **Balanced** | `{env}.{domain}.{resource}` |
| **Strict** | `{env}.{classification}.{domain}.{resource}.{version}` |
| **Custom** | User-defined YAML |

## Guardrail Policies

Environment별 config 검증 (min_insync_replicas, replication_factor 등)

## API Endpoints

**Topic Operations** (`/api/v1/topics`):  
- `GET /` - List topics (`?cluster_id=`)
- `POST /batch/upload` - YAML 업로드 & dry-run
- `POST /batch/dry-run` - Dry-run (JSON)
- `POST /batch/apply` - 배치 적용
- `POST /bulk-delete` - 일괄 삭제

**Policy Management** (`/api/v1/policies`):  
- `GET /` - 정책 목록
- `POST /` - 정책 생성
- `GET /{id}` - 정책 조회
- `PUT /{id}` - 정책 수정
- `POST /{id}/activate` - 정책 활성화
- `POST /{id}/archive` - 정책 아카이브
- `DELETE /{id}` - 정책 삭제

## Dependencies

- `shared`: Database, Event bus
- `cluster`: Kafka AdminClient
