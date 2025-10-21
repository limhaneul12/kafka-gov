# 🔌 Cluster Module

멀티 클러스터 연결 관리

## Structure

```
cluster/
├── domain/models/           # Cluster, ConnectionType, SecurityProtocol
├── application/use_cases/   # Register, Activate, Test connections
├── infrastructure/
│   ├── connectors.py       # Kafka/SR/MinIO/Connect clients
│   └── repositories.py
└── interface/routers/
    ├── broker.py
    ├── registry.py
    ├── storage.py
    └── connect.py
```

## Connection Types

- **Kafka**: Bootstrap servers, SASL/SSL
- **Schema Registry**: URL, HTTP auth
- **MinIO**: S3-compatible storage
- **Kafka Connect**: REST API

## API Endpoints

**Broker** (`/api/v1/clusters/broker`):  
- `GET /` - List Kafka clusters
- `POST /` - Register broker
- `POST /{id}/activate` - Activate
- `POST /{id}/test` - Test connection

**Registry** (`/api/v1/clusters/registry`):  
- `POST /` - Register Schema Registry
- `POST /{id}/activate`

**Storage** (`/api/v1/clusters/storage`):  
- `POST /` - Register MinIO
- `POST /{id}/activate`

**Connect** (`/api/v1/clusters/connect`):  
- `POST /` - Register Kafka Connect
- `POST /{id}/activate`
