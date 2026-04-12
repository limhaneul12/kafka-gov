# 🚀 Quick Start

Get Kafka-Gov running in 5 minutes!

## Prerequisites

- Docker & Docker Compose (recommended)
- OR: Python 3.12+, Node.js 18+

---

## Option 1: Docker Compose (Recommended)

Quickest way to get started:

```bash
# 1. Clone repository
git clone https://github.com/limhaneul12/kafka-gov.git
cd kafka-gov

# 2. Configure environment
cp .env.example .env
# Edit .env file with your Kafka connection details

# 3. Start the shipped services (app, frontend, nginx, redis)
#    Kafka and Schema Registry are expected on the external `kafka-network`
#    Metadata defaults to SQLite in /app/data unless KAFKA_GOV_DATABASE_URL is overridden
docker-compose up -d

# 4. Access web UI
open http://localhost:90
```

**Main Endpoints:**
- 🌐 **Web UI**: http://localhost:90
- 📚 **API Docs**: http://localhost:90/swagger (Swagger UI)
- 📖 **ReDoc**: http://localhost:90/redoc (Alternative API docs)
- 💚 **Health Check**: http://localhost:90/health

**Default Credentials:**
- No authentication required in development mode
- Production: Configure via environment variables

---

## Option 2: Local Development

Detailed setup for developers:

### Backend (Python 3.12+)
```bash
# Install Python dependencies (using uv)
cd kafka-gov
uv sync

# Run database migrations
uv run alembic upgrade head

# Start development server
uv run uvicorn app.main:app --reload --port 8000
```

Backend docs are available at `http://localhost:8000/swagger`.

### Frontend (React 19)
```bash
# Install Node.js dependencies
cd frontend
npm install

# Start development server
npm run dev
# Access at http://localhost:3000
```

---

## Next Steps

1. **Register Cluster**: UI → Connections → Add Cluster
2. **Configure Schema Policy**: Schema Policies → New Policy
3. **Upload Schemas**: Schemas → Upload Schema
4. **Review History**: History → Inspect approvals, overrides, and audit entries

---

## Troubleshooting

### Port conflicts
```bash
# Check if port 8000 is already in use
lsof -i :8000

# Change port in docker-compose.yml or .env
```

### Database connection errors
```bash
# Verify MySQL is running
docker ps | grep mysql

# Check database credentials in .env
```

### Kafka connection errors
```bash
# Test Kafka connectivity
telnet localhost 9092

# Verify KAFKA_BOOTSTRAP_SERVERS in .env
```

For more help, review the deployment notes in [Deployment Guide](../operations/deployment.md).
