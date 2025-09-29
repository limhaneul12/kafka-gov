<div align="center">
  <img src="https://raw.githubusercontent.com/limhaneul12/kafka-gov/main/image/logo.png" alt="Kafka Gov Logo" width="400"/>
  
  **🛡️ Kafka Topic & Schema Registry Governance Platform**
  
  [![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://python.org)
  [![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com)
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
- **Subject Management**: Organize schemas by subject with version control
- **File Upload**: Bulk schema upload with validation and conflict resolution
- **Storage Integration**: MinIO-backed schema artifact storage

### 🔒 **Security & Compliance**
- **JWT Authentication**: Secure API access with role-based permissions
- **Policy Engine**: Configurable rules for naming, configuration, and resource limits
- **Violation Detection**: Real-time policy violation detection with severity levels
- **Compliance Reporting**: Generate compliance reports for audit purposes

### 🏗️ **Enterprise Architecture**
- **Clean Architecture**: Domain-driven design with clear layer separation
- **High Performance**: Async/await throughout with connection pooling
- **Observability**: Structured logging, metrics, and health checks
- **Scalability**: Horizontal scaling support with stateless design

## 🏗️ Architecture

Built on **Clean Architecture** principles with domain-driven design:

```
app/
├── shared/                    # Common infrastructure
│   ├── database.py           # SQLAlchemy async engine
│   ├── container.py          # Dependency injection
│   └── auth.py              # JWT authentication
├── policy/                   # Policy engine domain
│   ├── domain/              # Policy rules & evaluation
│   ├── application/         # Policy services
│   └── infrastructure/      # Rule repositories
├── topic/                    # Topic management domain
│   ├── domain/              # Topic models & business logic
│   ├── application/         # Use cases & orchestration
│   ├── infrastructure/      # Kafka & database adapters
│   └── interface/           # REST API endpoints
├── schema/                   # Schema registry domain
│   └── (similar structure)
└── main.py                   # Application entry point
```

## 🚀 Quick Start

### Prerequisites
- Python 3.12+
- Docker & Docker Compose
- Kafka cluster
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

### Example Usage

```bash
# Register a new user
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "secure123"}'

# Plan topic changes
curl -X POST "http://localhost:8000/api/v1/topics/dev/batch/dry-run" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "topics": [
      {
        "name": "user-events",
        "action": "CREATE",
        "config": {
          "partitions": 3,
          "replication_factor": 2
        }
      }
    ]
  }'
```

## 🛠️ Tech Stack

| Category | Technology |
|----------|------------|
| **Framework** | FastAPI, Pydantic |
| **Database** | SQLAlchemy (Async), MySQL |
| **Message Broker** | Apache Kafka, Confluent Platform |
| **Storage** | MinIO (S3-compatible) |
| **Authentication** | JWT, Argon2 |
| **Architecture** | Clean Architecture, DDD |
| **Testing** | pytest, pytest-asyncio |
| **Type Safety** | Python 3.12+ strict typing |

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

#### Topic Management
```
GET    /api/v1/topics/{env}                    # List topics
GET    /api/v1/topics/{env}/{topic}            # Get topic details
POST   /api/v1/topics/{env}/batch/dry-run      # Plan topic changes
POST   /api/v1/topics/{env}/batch/apply        # Apply topic changes
GET    /api/v1/topics/{env}/plan/{change_id}   # Get execution plan
```

#### Schema Registry
```
GET    /api/v1/schemas/subjects                # List subjects
POST   /api/v1/schemas/{env}/batch/dry-run     # Plan schema changes
POST   /api/v1/schemas/{env}/batch/apply       # Apply schema changes
POST   /api/v1/schemas/{env}/upload            # Upload schema files
GET    /api/v1/schemas/{env}/plan/{change_id}  # Get schema plan
```

#### Authentication
```
POST   /api/v1/auth/register                   # Register user
POST   /api/v1/auth/login                      # Login user
```

#### System
```
GET    /health                                 # Health check
GET    /docs                                   # Swagger UI
GET    /redoc                                  # ReDoc
```

### 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific module tests
pytest tests/topic/
pytest tests/schema/
pytest tests/policy/
```

## 🚀 Deployment

### Docker Production

```bash
# Build production image
docker build -t kafka-gov:latest .

# Run with production settings
docker run -d \
  --name kafka-gov \
  -p 8000:8000 \
  --env-file .env.prod \
  kafka-gov:latest
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: kafka-gov
spec:
  replicas: 3
  selector:
    matchLabels:
      app: kafka-gov
  template:
    metadata:
      labels:
        app: kafka-gov
    spec:
      containers:
      - name: kafka-gov
        image: kafka-gov:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: kafka-gov-secrets
              key: database-url
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Setup

1. **Fork and clone**
   ```bash
   git clone https://github.com/limhaneul12/kafka-gov.git
   cd kafka-gov
   ```

2. **Set up development environment**
   ```bash
   uv sync --group dev
   pre-commit install
   ```

3. **Run tests**
   ```bash
   pytest
   ```

4. **Submit a pull request**

### Code Standards

- **Type Safety**: Full type hints with Python 3.12+
- **Testing**: 90%+ test coverage required
- **Documentation**: Docstrings for all public APIs
- **Formatting**: ruff
- **Architecture**: Follow Clean Architecture principles

## 💬 Community

- **Issues**: [GitHub Issues](https://github.com/limhaneul12/kafka-gov/issues)
- **Discussions**: [GitHub Discussions](https://github.com/limhaneul12/kafka-gov/discussions)
- **Security**: [Security Policy](SECURITY.md)

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com/) for the excellent web framework
- [Confluent](https://www.confluent.io/) for Kafka Python client
- [SQLAlchemy](https://www.sqlalchemy.org/) for database ORM
- [Pydantic](https://pydantic.dev/) for data validation

---

<div align="center">
  <strong>Built with ❤️ for the Kafka community</strong>
</div>