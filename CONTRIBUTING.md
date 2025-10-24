# 🤝 Contributing Guide

Thank you for contributing to the Kafka-Gov project! This document guides you on how to contribute and the coding standards to follow.

---

## 📋 Table of Contents

- [Getting Started](#-getting-started)
- [Development Environment Setup](#-development-environment-setup)
- [Code Style and Rules](#-code-style-and-rules)
- [Commit Convention](#-commit-convention)
- [Testing](#-testing)
- [Pull Request Process](#-pull-request-process)
- [Architecture Guide](#-architecture-guide)
- [Contact Us](#-contact-us)

---

## 🚀 Getting Started

### 1. Fork and Clone Repository

```bash
# Fork the repository on GitHub
# Then clone your fork
git clone https://github.com/YOUR_USERNAME/kafka-gov.git
cd kafka-gov

# Add upstream remote
git remote add upstream https://github.com/limhaneul12/kafka-gov.git
```

### 2. Create Branch

```bash
# Update to latest code
git checkout main
git pull upstream main

# Create feature branch
git checkout -b feature/your-feature-name
# Or bug fix branch
git checkout -b fix/your-bugfix-name
```

**Branch Naming Convention:**
- `feature/` - Add new features
- `fix/` - Bug fixes
- `docs/` - Documentation changes
- `refactor/` - Code refactoring
- `test/` - Add/modify tests
- `chore/` - Build settings, dependency updates, etc.

---

## 🛠️ Development Environment Setup

### Prerequisites

- **Python**: 3.12 or higher
- **uv**: Python package manager (ultra-fast dependency resolution)
- **Docker & Docker Compose**: For running local Kafka/Schema Registry
- **MySQL**: 8.0 or higher (or use Docker Compose)

### Install uv

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### Development Environment Setup

```bash
# 1. Create Python virtual environment and install dependencies
uv sync

# 2. Install pre-commit hooks
uv run pre-commit install

# 3. Set up environment variables
cp .env.example .env
# Edit .env file with your Kafka/DB connection details

# 4. Generate encryption key (for encrypting sensitive information)
uv run python generate_encryption_key.py

# 5. Run Kafka/Schema Registry with Docker Compose
docker-compose up -d

# 6. Run database migrations
uv run alembic upgrade head

# 7. Start application
uv run uvicorn app.main:app --reload
```

**Application Access:**
- Web UI: http://localhost:8000
- API Docs: http://localhost:8000/swagger
- Health Check: http://localhost:8000/health

---

## 📏 Code Style and Rules

### Basic Principles

The project is based on **Python 3.12+** and follows these principles:

1. **Type Safety**: All functions/classes use strict type hints
2. **Boundary Separation**: Clear separation between IO boundary (Pydantic) and internal domain (dataclasses)
3. **Minimal Validation**: Validate once at input, avoid redundant validation internally
4. **Test First**: Write pytest-based unit tests first
5. **Dependency Management**: Manage with uv, avoid adding unnecessary libraries

### Type Hint Rules

```python
# ✅ Correct example (Python 3.12+ native syntax)
def process_data(items: list[str], config: dict[str, int]) -> str | None:
    """Data processing function"""
    ...

# ❌ Incorrect example (legacy syntax)
from typing import Optional, List, Dict

def process_data(items: List[str], config: Dict[str, int]) -> Optional[str]:
    ...
```

**Type Hint Standards:**
- Use `list[T]` (❌ `List[T]`)
- Use `dict[K, V]` (❌ `Dict[K, V]`)
- Use `str | None` (❌ `Optional[str]`)
- Use `tuple[T, ...]` (❌ `Tuple[T, ...]`)

### Data Model Rules

**IO Boundary (External Input/Output)**
```python
from pydantic import BaseModel, Field

class CreateTopicRequest(BaseModel):
    """API request model - requires runtime validation"""
    name: str = Field(..., pattern=r'^[a-z0-9\-\.]+$')
    partitions: int = Field(..., ge=1)
    replication_factor: int = Field(..., ge=1)
```

**Internal Domain (Business Logic)**
```python
from dataclasses import dataclass
from datetime import datetime

@dataclass(frozen=True)
class Topic:
    """Domain model - immutable structure"""
    name: str
    partitions: int
    replication_factor: int
    created_at: datetime
```

### No Lazy Loading

```python
# ❌ Absolutely forbidden
def process():
    from app.shared.domain.events import DomainEvent  # No imports inside functions
    ...

# ✅ Correct way
from app.shared.domain.events import DomainEvent

def process():
    ...
```

### Code Formatting and Linting

The project uses **Ruff** for automatic formatting and linting.

```bash
# Code formatting
uv run ruff format .

# Linting (auto-fixable items)
uv run ruff check --fix .

# Linting (check only, no fixes)
uv run ruff check .
```

**Pre-commit hooks run automatically:**
- Automatic Ruff formatting and linting on commit
- Commit fails if violations exist → fix and retry

---

## 📝 Commit Convention

### Conventional Commits Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Type:**
- `feat`: Add new features
- `fix`: Bug fixes
- `docs`: Documentation changes
- `style`: Code formatting (no functional changes)
- `refactor`: Code refactoring
- `test`: Add/modify tests
- `chore`: Build settings, dependency updates, etc.
- `perf`: Performance improvements

**Scope (Optional):**
- `topic`, `schema`, `connect`, `cluster`, `shared`

### Examples

```bash
# Add feature
git commit -m "feat(connect): Add connector pause/resume endpoints"

# Bug fix
git commit -m "fix(schema): Fix compatibility check validation"

# Documentation update
git commit -m "docs: Update API reference for Connect endpoints"

# Refactoring
git commit -m "refactor(topic): Extract validation logic to domain service"
```

---

## 🧪 Testing

### Testing Principles

1. **Unit Test First**: Domain logic must have unit tests
2. **80%+ Coverage**: New code must maintain minimum 80% test coverage
3. **Fixture Usage**: Use pytest fixtures for test data reuse
4. **Async Testing**: Use `pytest-asyncio`

### Running Tests

```bash
# Run all tests
uv run pytest

# With coverage
uv run pytest --cov=app --cov-report=html

# Test specific module
uv run pytest tests/connect/

# Test specific file
uv run pytest tests/connect/test_connector_service.py

# Re-run failed tests only
uv run pytest --lf

# Parallel execution (faster)
uv run pytest -n auto
```

### Test Writing Example

```python
# tests/connect/test_connector_service.py
import pytest
from app.connect.application.services import ConnectorService
from app.connect.domain.models import ConnectorInfo, ConnectorType, ConnectorState

@pytest.fixture
def mock_connector_info():
    """Test connector info fixture"""
    return ConnectorInfo(
        name="test-connector",
        type=ConnectorType.SOURCE,
        state=ConnectorState.RUNNING,
        worker_id="worker-1",
        config={"connector.class": "io.debezium.connector.mysql.MySqlConnector"},
        tasks=[],
        topics=["test.topic"],
    )

@pytest.mark.asyncio
async def test_get_connector_info(connector_service: ConnectorService, mock_connector_info):
    """Test connector info retrieval"""
    # Given
    connector_name = "test-connector"
    
    # When
    result = await connector_service.get_connector(connector_name)
    
    # Then
    assert result.name == connector_name
    assert result.type == ConnectorType.SOURCE
    assert result.state == ConnectorState.RUNNING
```

---

## 🔄 Pull Request Process

### 1. Pre-PR Checklist

- [ ] All tests pass (`uv run pytest`)
- [ ] Code coverage 80%+ maintained
- [ ] Ruff formatting and linting pass
- [ ] No missing type hints
- [ ] Documentation updated (if API changed)
- [ ] Commit messages follow convention

### 2. Create PR

```bash
# Push branch
git push origin feature/your-feature-name

# Create Pull Request on GitHub
```

### 3. PR Description Template

```markdown
## 📋 Changes

<!-- Brief description of what was changed -->

## 🎯 Reason for Change

<!-- Explain why this change was needed -->

## 🧪 Testing

<!-- Explain how you tested this -->

## 📸 Screenshots (Optional)

<!-- Attach screenshots if there are UI changes -->

## ✅ Checklist

- [ ] Tests written
- [ ] Documentation updated
- [ ] Ready for code review
```

### 4. Code Review Response

- Respond politely to reviewer feedback
- Implement requested changes and add commits
- Discuss items needing debate in PR comments

### 5. Merge Conditions

- **Minimum 1 Approval** required
- **All CI tests pass**
- **No conflicts**

---

## 🏗️ Architecture Guide

### Clean Architecture Layers

The project follows Clean Architecture principles:

```
app/
├── [domain]/
│   ├── domain/              # Domain models (business rules)
│   │   ├── models.py       # dataclass immutable structures
│   │   ├── repositories.py # Repository interfaces (ABC)
│   │   ├── services.py     # Domain services
│   │   └── events.py       # Domain events
│   │
│   ├── application/         # Use cases (application logic)
│   │   ├── use_cases.py    # Use case implementations
│   │   ├── dtos.py         # DTOs (Pydantic)
│   │   └── mappers.py      # DTO ↔ Domain conversion
│   │
│   ├── infrastructure/      # External adapters (DB, API clients)
│   │   ├── models.py       # SQLAlchemy models
│   │   ├── repositories.py # Repository implementations
│   │   └── client.py       # External API clients
│   │
│   └── interface/           # Interface adapters (API routers)
│       └── router.py        # FastAPI routers
```

### Dependency Direction

```
Interface → Application → Domain ← Infrastructure
```

- **Domain**: No dependencies (pure business logic)
- **Application**: Depends only on Domain
- **Infrastructure**: Implements Domain interfaces
- **Interface**: Calls Application

### New Feature Addition Example

**1. Define Domain Model**
```python
# app/connect/domain/models.py
from dataclasses import dataclass
from enum import Enum

@dataclass(frozen=True)
class Connector:
    """Connector domain model"""
    name: str
    type: ConnectorType
    state: ConnectorState
    config: dict[str, str]
```

**2. Repository Interface**
```python
# app/connect/domain/repositories.py
from abc import ABC, abstractmethod

class ConnectorRepository(ABC):
    """Connector repository interface"""
    
    @abstractmethod
    async def find_by_name(self, name: str) -> Connector | None:
        ...
```

**3. Repository Implementation**
```python
# app/connect/infrastructure/repositories.py
class ConnectorRepositoryImpl(ConnectorRepository):
    """Connector repository implementation"""
    
    async def find_by_name(self, name: str) -> Connector | None:
        # Query DB with SQLAlchemy
        ...
```

**4. Write UseCase**
```python
# app/connect/application/use_cases.py
class GetConnectorUseCase:
    """Connector retrieval use case"""
    
    def __init__(self, repository: ConnectorRepository):
        self.repository = repository
    
    async def execute(self, name: str) -> ConnectorDTO:
        connector = await self.repository.find_by_name(name)
        if not connector:
            raise ConnectorNotFoundError(name)
        return ConnectorMapper.to_dto(connector)
```

**5. Add API Router**
```python
# app/connect/interface/router.py
@router.get("/connectors/{name}")
async def get_connector(
    name: str,
    use_case: GetConnectorUseCase = Depends(Provide[...])
):
    return await use_case.execute(name)
```

---

## 🎨 Using Domain Events

### Event Publishing

```python
# Define domain event
class ConnectorCreatedEvent(DomainEvent):
    connector_name: str
    connector_type: ConnectorType

# Publish event
from app.shared.domain.event_bus import EventBus

await event_bus.publish(ConnectorCreatedEvent(
    connector_name="my-connector",
    connector_type=ConnectorType.SOURCE
))
```

### Event Subscription

```python
# Register event handler
@event_bus.subscribe(ConnectorCreatedEvent)
async def on_connector_created(event: ConnectorCreatedEvent):
    logger.info(f"Connector created: {event.connector_name}")
    # Follow-up actions (e.g., auto-create topics)
```

---

## 📚 References

- [Clean Architecture](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [Python 3.12 Documentation](https://docs.python.org/3.12/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Confluent Kafka Python](https://docs.confluent.io/kafka-clients/python/current/overview.html)
- [pytest Documentation](https://docs.pytest.org/)
- [Conventional Commits](https://www.conventionalcommits.org/)

---

## 💬 Contact Us

If you have questions or suggestions:

1. **GitHub Issues**: Bug reports, feature requests
2. **GitHub Discussions**: General questions, idea sharing
3. **Pull Request**: Direct contributions

---

## 🙏 Thank You!

Your contributions make Kafka-Gov a better project. 🎉

**Happy coding!** 🚀
