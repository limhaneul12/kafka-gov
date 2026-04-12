# 🔌 Cluster Module

멀티 클러스터 연결 관리

## Structure

```
cluster/
├── domain/models/           # Cluster, ConnectionType, SecurityProtocol
├── application/use_cases/   # Register, Activate, Test connections
├── infrastructure/
│   └── repositories.py
└── interface/routers/
    ├── broker.py
    └── registry.py
```

## Connection Types

- **Kafka**: Bootstrap servers, SASL/SSL
- **Schema Registry**: URL, HTTP auth

## API Endpoints

**Broker** (`/api/v1/clusters/brokers`):  
- `GET /` - List Kafka clusters
- `POST /` - Register broker
- `POST /{id}/activate` - Activate
- `POST /{id}/test` - Test connection

**Registry** (`/api/v1/clusters/schema-registries`):  
- `POST /` - Register Schema Registry
- `POST /{id}/activate`
