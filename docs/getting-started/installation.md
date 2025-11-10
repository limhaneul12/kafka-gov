# 📦 Installation Guide

Complete installation guide for Kafka-Gov.

## System Requirements

**Minimum Requirements:**
- **CPU**: 2 cores
- **Memory**: 4GB RAM
- **Disk**: 10GB free space
- **OS**: Linux, macOS, Windows (with WSL2)

**Software Requirements:**
- Docker 20.10+ & Docker Compose 2.0+ (for containerized deployment)
- Python 3.12+ (for local development)
- Node.js 18+ (for frontend development)
- MySQL 8.0+ (for metadata storage)

---

## Installation Methods

### 1. Docker Compose (Production-Ready)

```bash
# Clone repository
git clone https://github.com/limhaneul12/kafka-gov.git
cd kafka-gov

# Create environment file
cp .env.example .env

# Edit .env with your settings
nano .env

# Start all services
docker-compose up -d

# Verify services are running
docker-compose ps
```

### 2. Local Development Setup

#### Backend Setup

```bash
# Install uv (Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install Python dependencies
cd kafka-gov
uv sync

# Generate encryption key
python generate_encryption_key.py
# Copy output to .env as ENCRYPTION_KEY

# Run database migrations
uv run alembic upgrade head

# Start backend server
uv run uvicorn app.main:app --reload --port 8000
```

#### Frontend Setup

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

---

## Configuration

### Generate Encryption Key

Encryption key is required for storing sensitive credentials:

```bash
python generate_encryption_key.py
```

Copy the output to `.env`:
```bash
ENCRYPTION_KEY=your-generated-key-here
```

### Configure Database

Edit `.env`:
```bash
DATABASE_URL=mysql+aiomysql://user:password@localhost:3306/kafka_gov
```

### Configure Kafka Connection (Optional)

For initial cluster registration:
```bash
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_SECURITY_PROTOCOL=PLAINTEXT
```

See [Configuration Guide](./configuration.md) for all available options.

---

## Post-Installation

### Verify Installation

1. **Check Health Endpoint:**
```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "database": "connected",
  "version": "1.0.0"
}
```

2. **Access Web UI:**
Open http://localhost:8000 in your browser

3. **Check API Docs:**
Visit http://localhost:8000/docs

### Initial Setup

1. **Register First Cluster:**
   - Navigate to Connections page
   - Click "Add Cluster"
   - Enter bootstrap servers and credentials

2. **Create First Policy:**
   - Go to Policies page
   - Click "Create Policy"
   - Select environment and set rules

3. **Create Test Topic:**
   - Navigate to Topics page
   - Click "Create Topic"
   - Fill in metadata and submit

---

## Upgrading

### Docker Compose

```bash
# Pull latest images
docker-compose pull

# Restart services
docker-compose down
docker-compose up -d
```

### Local Development

```bash
# Update Python dependencies
uv sync --upgrade

# Run migrations
uv run alembic upgrade head

# Update frontend dependencies
cd frontend
npm update
```

---

## Uninstallation

### Docker Compose

```bash
# Stop and remove containers
docker-compose down

# Remove volumes (WARNING: deletes all data)
docker-compose down -v
```

### Local Development

```bash
# Remove Python virtual environment
rm -rf .venv

# Remove frontend node_modules
cd frontend
rm -rf node_modules
```

---

## Next Steps

- [Quick Start Guide](./quick-start.md)
- [Configuration Reference](./configuration.md)
- [Architecture Overview](../architecture/overview.md)
