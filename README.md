<div align="center">
  <img src="https://raw.githubusercontent.com/limhaneul12/kafka-gov/main/image/logo.png" alt="Kafka Gov Logo" width="400"/>
  
  **🛡️ Kafka Topic & Schema Registry Governance Platform**
  
  [![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://python.org)
  [![FastAPI](https://img.shields.io/badge/FastAPI-0.117+-green.svg)](https://fastapi.tiangolo.com)
  [![Confluent Kafka](https://img.shields.io/badge/Confluent_Kafka-2.6.1+-red.svg)](https://docs.confluent.io/platform/current/clients/confluent-kafka-python/html/index.html)
  [![Coverage](https://img.shields.io/badge/Coverage-85%25-brightgreen.svg)](https://github.com/limhaneul12/kafka-gov)
  [![License](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
  [![pytest](https://img.shields.io/badge/pytest-8.4.2-blue.svg)](https://github.com/limhaneul12/kafka-gov/actions)
  [![CI](https://github.com/limhaneul12/kafka-gov/workflows/CI/badge.svg)](https://github.com/limhaneul12/kafka-gov/actions)
  
  [🚀 Quick Start](#-quick-start) • [📖 Documentation](#-documentation) • [🤝 Contributing](#-contributing) • [💬 Community](#-community)
</div>

--- 

## ✨ Features

### 🎯 **Topic Management**
- **Batch Operations**: Plan and execute multiple topic changes with dry-run support
- **Policy Enforcement**: Automated validation against naming conventions and configuration rules
- **Environment-aware**: DEV/STG/PROD environment separation with different policies
- **Audit Trail**: Complete history of all topic changes with rollback capabilities

### 📋 **Schema Registry Governance**
- **Schema Evolution**: Manage schema versions with compatibility validation
- **File Upload**: Bulk schema upload (.avsc, .json, .proto, .zip) with auto-registration
- **Storage Integration**: MinIO-backed schema artifact storage
- **Schema Management**: Delete impact analysis and safe schema deletion
- **Schema Sync**: Automatic synchronization from Schema Registry to database

### 🔒 **Policy & Governance**
- **Integrated Policy Engine**: Topic and Schema policies with environment-specific rules
- **Violation Detection**: Real-time policy violation detection with severity levels (WARNING, ERROR, CRITICAL)
- **Audit Trail**: Complete audit logging for Topic and Schema operations
- **Role-Based Access**: User role management (VIEWER, DEVELOPER, ADMIN)

### 📊 **Analysis & Monitoring**
- **Topic-Schema Correlation**: Automatic linking between topics and schemas
- **Impact Analysis**: Schema deletion impact analysis with affected topics
- **Activity Dashboard**: Unified audit activity view across all components
- **Cluster Status**: Real-time Kafka cluster health monitoring

### 🏗️ **Architecture**
- **Clean Architecture**: Domain-driven design with clear layer separation
- **Event-Driven**: Domain events for cross-context communication
- **High Performance**: Async/await throughout with connection pooling
- **Type Safety**: Python 3.12+ with strict type hints and pyrefly validation
- **Observability**: Structured logging, metrics, and health checks
- **Scalability**: Horizontal scaling support with stateless design

## 🏗️ Architecture

Built on **Clean Architecture** principles with domain-driven design:

```
app/
├── shared/          # Common infrastructure & domain events
├── topic/           # Topic management domain
├── schema/          # Schema registry domain
├── analysis/        # Analysis & correlation domain
├── container.py     # Root DI container
└── main.py          # FastAPI application
```

**Key Principles:**
- **Clean Architecture**: Domain → Application → Infrastructure → Interface
- **Event-Driven**: Domain events for cross-context communication
- **Type Safety**: Python 3.12+ with strict typing and pyrefly validation
- **DI Container**: Hierarchical dependency injection with `dependency-injector`

### Prerequisites
- Python 3.12+
- Docker & Docker Compose
- Kafka cluster with Schema Registry
- MySQL/PostgreSQL database

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/limhaneul12/kafka-gov.git
   cd kafka-gov
   ```

2. **Set up environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Install dependencies**
   ```bash
   # Using uv (recommended)
   uv sync
   
   # Or using pip
   pip install -r requirements.txt
   ```

4. **Start with Docker Compose**
   ```bash
   docker-compose up -d
   ```

5. **Access the application**
   - API: http://localhost:8000
   - Swagger UI: http://localhost:8000/docs
   - Health Check: http://localhost:8000/health

### Quick Start Example

```bash
# Start services
docker-compose up -d

# Access Swagger UI
open http://localhost:8000/docs

# Health check
curl http://localhost:8000/health
```

## 🛠️ Tech Stack

| Category | Technology |
|----------|------------|
| **Framework** | FastAPI 0.117+, Pydantic v2 |
| **Domain Models** | msgspec (high-performance serialization) |
| **Database** | SQLAlchemy 2.0 (Async), MySQL/PostgreSQL |
| **Message Broker** | Apache Kafka, Confluent Platform |
| **Schema Registry** | Confluent Schema Registry |
| **Storage** | MinIO (S3-compatible) |
| **Dependency Injection** | dependency-injector |
| **Event Bus** | In-memory async event bus |
| **Architecture** | Clean Architecture, DDD, Event-Driven |
| **Testing** | pytest, pytest-asyncio, pytest-cov (85% coverage) |
| **Type Safety** | Python 3.12+, pyrefly, ruff |
| **Package Manager** | uv (ultra-fast) |
| **Main Libraries** | confluent-kafka, aiomysql, httpx, orjson |

## 📖 Documentation

### 🔧 Configuration

Key environment variables:

```bash
# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
SCHEMA_REGISTRY_URL=http://localhost:8081

# Database
DATABASE_URL=mysql+aiomysql://user:pass@localhost/kafka_gov

# Storage
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin

# Authentication
SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1800
```

### 🛡️ API Endpoints

#### Topic Management (`/api/v1/topics`)
```
POST   /batch/dry-run                          # Plan topic changes (dry-run)
POST   /batch/apply                            # Apply topic changes
GET    /plan/{change_id}                       # Get plan by change ID
GET    /detail/{topic_name}                    # Get topic details
GET    /list                                   # List all topics
DELETE /bulk-delete                            # Bulk delete topics
```

#### Schema Registry (`/api/v1/schemas`)
```
POST   /batch/dry-run                          # Plan schema changes (dry-run)
POST   /batch/apply                            # Apply schema changes
POST   /upload                                 # Upload schema files (.avsc, .json, .proto, .zip)
GET    /plan/{change_id}                       # Get schema plan
POST   /sync                                   # Sync from Schema Registry to DB
POST   /delete/analyze                         # Analyze schema deletion impact
DELETE /delete/{subject}                       # Delete schema (with force option)
GET    /list                                   # List all schemas
```

#### Analysis & Correlation (`/api/v1/analysis`)
```
GET    /correlation/by-schema/{subject}        # Get topics using a schema
GET    /correlation/by-topic/{topic_name}      # Get schema correlation for topic
POST   /correlation/link                       # Manually link topic to schema
GET    /impact/schema/{subject}                # Get schema impact analysis
```

#### Shared (`/api/v1`)
```
GET    /cluster/status                         # Kafka cluster status
GET    /audit/activities                       # Recent audit activities
GET    /audit/activity/{activity_id}           # Get activity detail
```

#### System
```
GET    /health                                 # Health check
GET    /docs                                   # Swagger UI
GET    /redoc                                  # ReDoc
```

## 🚀 Deployment

```bash
# Build and run with Docker Compose
docker-compose up -d

# Or build production image
docker build -t kafka-gov:latest .
docker run -d -p 8000:8000 --env-file .env.prod kafka-gov:latest
```



## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Run tests: `uv run pytest --cov=app`
4. Submit a pull request

**Standards**: Python 3.12+, 80%+ test coverage, Clean Architecture

## 💬 Community

- **Issues**: [GitHub Issues](https://github.com/limhaneul12/kafka-gov/issues)
- **Discussions**: [GitHub Discussions](https://github.com/limhaneul12/kafka-gov/discussions)
- **Security**: [Security Policy](SECURITY.md)

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com/) for the excellent async web framework
- [Confluent](https://www.confluent.io/) for Kafka Python client and Schema Registry
- [SQLAlchemy](https://www.sqlalchemy.org/) for async database ORM
- [Pydantic](https://pydantic.dev/) for data validation
- [msgspec](https://jcristharif.com/msgspec/) for high-performance serialization
- [dependency-injector](https://python-dependency-injector.ets-labs.org/) for DI container
- [uv](https://github.com/astral-sh/uv) for ultra-fast package management
- [pyrefly](https://github.com/pyrefly-labs/pyrefly) for advanced type checking

---

<div align="center">
  <strong>Built with ❤️ for the Kafka community</strong>
</div>