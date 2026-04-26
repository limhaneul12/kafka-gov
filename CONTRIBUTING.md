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
- Web UI (frontend dev server): http://localhost:3000
- Backend API Docs: http://localhost:8000/swagger
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

class SchemaBatchItemRequest(BaseModel):
    """API request model - requires runtime validation"""
    subject: str = Field(..., pattern=r'^(dev|stg|prod)\.[a-z0-9_.\-]+$')
    schema_type: str = Field(..., pattern=r'^(AVRO|JSON|PROTOBUF)$')
    compatibility: str = Field(..., pattern=r'^(BACKWARD|FULL|NONE)$')
```

**Internal Domain (Business Logic)**
```python
from dataclasses import dataclass

@dataclass(frozen=True)
class SchemaRule:
    """Domain model - immutable structure"""
    subject: str
    compatibility: str
```

### No Lazy Loading

```python
# ❌ Absolutely forbidden
def process():
    from app.schema.governance_support.events import DomainEvent  # No imports inside functions
    ...

# ✅ Correct way
from app.schema.governance_support.events import DomainEvent

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
- `schema`, `cluster`, `shared`, `docs`, `frontend`

### Examples

```bash
# Add feature
git commit -m "feat(schema): Add known-topic hint endpoint"

# Bug fix
git commit -m "fix(schema): Fix compatibility check validation"

# Documentation update
git commit -m "docs: Update schema governance API reference"

# Refactoring
git commit -m "refactor(schema): Extract validation logic to domain service"
```

---

## 🧪 Testing

### Testing Principles

1. **Unit Test First**: Domain logic must have unit tests
2. **Coverage Discipline**: New code must keep the enforced coverage threshold green and include focused regressions for behavior changes
3. **Fixture Usage**: Use pytest fixtures for test data reuse
4. **Async Testing**: Use `pytest-asyncio`

### Running Tests

```bash
# Run all tests
uv run pytest

# With coverage
uv run pytest --cov=app --cov-report=html

# Test specific file
uv run pytest tests/test_schema_domain_models.py

# Re-run failed tests only
uv run pytest --lf

# Parallel execution (faster)
uv run pytest -n auto
```

### Test Writing Example

```python
# tests/test_schema_domain_models.py
import pytest
from app.schema.domain.models.spec_batch import DomainSchemaSpec
from app.schema.domain.models.types_enum import DomainCompatibilityMode, DomainSchemaType
from app.schema.domain.models.value_objects import DomainSchemaMetadata, DomainSchemaSource

@pytest.fixture
def schema_spec():
    return DomainSchemaSpec(
        subject="dev.orders-value",
        schema_type=DomainSchemaType.AVRO,
        compatibility=DomainCompatibilityMode.BACKWARD,
        source=DomainSchemaSource(type="INLINE", inline='{"type":"record","name":"Order","fields":[]}'),
        metadata=DomainSchemaMetadata(owner="team-data", doc="https://wiki/orders"),
    )

def test_schema_spec_has_owner(schema_spec):
    assert schema_spec.metadata.owner == "team-data"
    assert schema_spec.subject == "dev.orders-value"
```

---

## 🔄 Pull Request Process

### 1. Pre-PR Checklist

- [ ] All tests pass (`uv run pytest`)
- [ ] Coverage gate remains green for the affected test suite
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
# app/schema/domain/models/spec_batch.py
from dataclasses import dataclass

@dataclass(frozen=True)
class SchemaRule:
    subject: str
    compatibility: str
```

**2. Repository Interface**
```python
# app/schema/domain/repositories/interfaces.py
from abc import ABC, abstractmethod

class SchemaRepository(ABC):
    
    @abstractmethod
    async def get_latest(self, subject: str):
        ...
```

**3. Repository Implementation**
```python
# app/schema/infrastructure/repository/mysql_repository.py
class SchemaRepositoryImpl(SchemaRepository):
    
    async def get_latest(self, subject: str):
        ...
```

**4. Write UseCase**
```python
# app/schema/application/use_cases/management/search.py
class SearchSchemasUseCase:
    
    def __init__(self, repository: SchemaRepository):
        self.repository = repository
    
    async def execute(self, subject: str):
        return await self.repository.get_latest(subject)
```

**5. Add API Router**
```python
# app/schema/interface/routers/management_router.py
@router.get("/search")
async def search_schemas(
    subject: str,
    use_case: SearchSchemasUseCase = Depends(Provide[...])
):
    return await use_case.execute(subject)
```

---

## 🎨 Using Domain Events

### Event Publishing

```python
# Define domain event
class SchemaRegisteredEvent(DomainEvent):
    subject: str
    schema_type: str

# Publish event
from app.shared.domain.event_bus import EventBus

await event_bus.publish(SchemaRegisteredEvent(
    subject="dev.orders-value",
    schema_type="AVRO",
))
```

### Event Subscription

```python
# Register event handler
@event_bus.subscribe(SchemaRegisteredEvent)
async def on_schema_registered(event: SchemaRegisteredEvent):
    logger.info(f"Schema registered: {event.subject}")
    # Follow-up actions (e.g., write audit metadata)
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
