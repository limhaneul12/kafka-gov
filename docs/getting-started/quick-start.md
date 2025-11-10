# 🚀 Quick Start

Get Kafka-Gov running in 5 minutes!

## Prerequisites

- Docker & Docker Compose (recommended)
- OR: Python 3.12+, Node.js 18+, MySQL 8.0+

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

# 3. Start all services (Kafka, MySQL, MinIO, Backend, Frontend)
docker-compose up -d

# 4. Access web UI
open http://localhost:8000
```

**Main Endpoints:**
- 🌐 **Web UI**: http://localhost:8000
- 📚 **API Docs**: http://localhost:8000/docs (Swagger UI)
- 📖 **ReDoc**: http://localhost:8000/redoc (Alternative API docs)
- 💚 **Health Check**: http://localhost:8000/health

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

### Frontend (React 19)
```bash
# Install Node.js dependencies
cd frontend
npm install

# Start development server
npm run dev
# Access at http://localhost:5173
```

---

## Test Your First Batch Upload

```bash
# Test batch creation with YAML file
curl -X POST "http://localhost:8000/api/v1/topics/batch/upload" \
  -F "file=@example/batch_topics.yml"

# Result: Dry-run preview → Review policy violations → Click "Apply Changes"
```

---

## Next Steps

1. **Register Cluster**: UI → Connections → Add Cluster
2. **Configure Policy**: Policies → Create Policy
3. **Create Topics**: Topics → Create Topic (single) or Upload YAML (batch)
4. **Upload Schemas**: Schemas → Upload Schema

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

For more help, see [Troubleshooting Guide](../operations/troubleshooting.md).
