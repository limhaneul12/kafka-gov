# 🔌 Connect Module

Kafka Connect 커넥터 관리

## Structure

```
connect/
├── domain/models/          # Connector, Task, ConnectorStatus
├── application/use_cases/  # CRUD, Control, Validation
├── infrastructure/
│   └── connect_client.py  # Kafka Connect REST API
└── interface/routers/
    ├── connector_crud_router.py
    ├── connector_control_router.py
    ├── tasks_router.py
    ├── plugins_router.py
    └── metadata_router.py
```

## Connector Types

- **SOURCE**: 외부 → Kafka (e.g., JDBC, Debezium)
- **SINK**: Kafka → 외부 (e.g., S3, Elasticsearch)

## API Endpoints

**CRUD** (`/api/v1/connect/connectors`):  
- `GET /` - List connectors
- `POST /` - Create connector
- `GET /{name}` - Get details
- `PUT /{name}/config` - Update config
- `DELETE /{name}` - Delete

**Control**:  
- `PUT /{name}/pause` - Pause
- `PUT /{name}/resume` - Resume
- `POST /{name}/restart` - Restart

**Tasks** (`/api/v1/connect/connectors/{name}/tasks`):  
- `GET /` - List tasks
- `POST /{id}/restart` - Restart task

**Plugins** (`/api/v1/connect/plugins`):  
- `GET /` - List installed plugins
- `PUT /{class}/validate` - Validate config
