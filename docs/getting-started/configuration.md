# ⚙️ Configuration Guide

Complete configuration reference for Kafka-Gov.

## Environment Variables

### Required Variables

These must be set for Kafka-Gov to run:

```bash
# Database Connection (REQUIRED)
DATABASE_URL=mysql+aiomysql://user:password@host:3306/kafka_gov

# Encryption Key (REQUIRED)
# Generate using: python generate_encryption_key.py
ENCRYPTION_KEY=your-generated-encryption-key-here

# Application Environment (REQUIRED)
ENVIRONMENT=production  # development, staging, production

# CORS Origins (REQUIRED for production)
CORS_ORIGINS=https://kafka-gov.company.com,https://app.company.com
```

---

### Optional Variables

#### Application Settings

```bash
# Logging
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL

# API Configuration
API_PREFIX=/api/v1
DOCS_URL=/docs
REDOC_URL=/redoc
```

#### Default Kafka Cluster

Configure a default cluster for initial registration:

```bash
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_SECURITY_PROTOCOL=PLAINTEXT  # PLAINTEXT, SSL, SASL_PLAINTEXT, SASL_SSL

# SASL Configuration (if using SASL)
KAFKA_SASL_MECHANISM=PLAIN  # PLAIN, SCRAM-SHA-256, SCRAM-SHA-512, GSSAPI
KAFKA_SASL_USERNAME=admin
KAFKA_SASL_PASSWORD=admin-secret

# Timeouts
KAFKA_REQUEST_TIMEOUT_MS=30000
KAFKA_SESSION_TIMEOUT_MS=10000
```

#### Schema Registry

```bash
SCHEMA_REGISTRY_URL=http://localhost:8081
SCHEMA_REGISTRY_BASIC_AUTH=username:password  # Optional
```

#### Object Storage (MinIO/S3)

```bash
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=kafka-gov
MINIO_SECURE=false  # true for HTTPS
```

#### Kafka Connect

```bash
KAFKA_CONNECT_URL=http://localhost:8083
KAFKA_CONNECT_BASIC_AUTH=username:password  # Optional
```

---

## Configuration File

### .env File

Create `.env` file in project root:

```bash
# Copy from example
cp .env.example .env

# Edit with your settings
nano .env
```

### Environment-Specific Files

Maintain separate configs per environment:

```
.env.development
.env.staging
.env.production
```

Load specific environment:
```bash
# Docker Compose
docker-compose --env-file .env.production up -d

# Manual
export $(cat .env.production | xargs) && uvicorn app.main:app
```

---

## Security Configuration

### Generate Encryption Key

```bash
python generate_encryption_key.py
```

Copy the output to your `.env` file:
```bash
ENCRYPTION_KEY=base64-encoded-key-here
```

### Rotate Encryption Key

1. Generate new key
2. Update `ENCRYPTION_KEY` in `.env`
3. Restart application
4. Re-register clusters (credentials will be re-encrypted)

---

## Database Configuration

### MySQL Setup

```sql
CREATE DATABASE kafka_gov CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'kafka_gov'@'%' IDENTIFIED BY 'strong-password';
GRANT ALL PRIVILEGES ON kafka_gov.* TO 'kafka_gov'@'%';
FLUSH PRIVILEGES;
```

### Connection URL Format

```
mysql+aiomysql://username:password@host:port/database?charset=utf8mb4
```

### Connection Pool Settings

```bash
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20
DATABASE_POOL_TIMEOUT=30
DATABASE_POOL_RECYCLE=3600
```

---

## CORS Configuration

### Development

```bash
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

### Production

```bash
# Specific domains only
CORS_ORIGINS=https://kafka-gov.company.com,https://app.company.com

# Multiple environments
CORS_ORIGINS=https://kafka-gov.company.com,https://kafka-gov-staging.company.com
```

---

## Logging Configuration

### Log Levels

```bash
LOG_LEVEL=DEBUG   # All logs
LOG_LEVEL=INFO    # Standard logs (recommended)
LOG_LEVEL=WARNING # Warnings and errors only
LOG_LEVEL=ERROR   # Errors only
```

### Structured Logging

Kafka-Gov uses structured JSON logging:

```json
{
  "timestamp": "2025-01-15T10:30:00Z",
  "level": "INFO",
  "module": "topic.application",
  "message": "Topic created successfully",
  "topic_name": "prod.orders.created",
  "user": "admin",
  "trace_id": "abc123"
}
```

---

## Configuration Validation

### Check Configuration

```bash
# Validate env vars
uv run python -c "from app.config import settings; print(settings)"

# Test database connection
uv run python -c "from app.shared.infrastructure.database import get_session; import asyncio; asyncio.run(get_session().__anext__())"
```

### Health Check

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

---

## Example Configurations

### Development

```bash
ENVIRONMENT=development
LOG_LEVEL=DEBUG
DATABASE_URL=mysql+aiomysql://root:root@localhost:3306/kafka_gov_dev
ENCRYPTION_KEY=dev-encryption-key-not-for-production
CORS_ORIGINS=http://localhost:5173
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
```

### Production

```bash
ENVIRONMENT=production
LOG_LEVEL=INFO
DATABASE_URL=mysql+aiomysql://kafka_gov:strong-password@db.company.com:3306/kafka_gov
ENCRYPTION_KEY=base64-production-key-keep-secret
CORS_ORIGINS=https://kafka-gov.company.com
KAFKA_BOOTSTRAP_SERVERS=kafka-prod-1:9092,kafka-prod-2:9092,kafka-prod-3:9092
KAFKA_SECURITY_PROTOCOL=SASL_SSL
KAFKA_SASL_MECHANISM=SCRAM-SHA-512
```

---

## Troubleshooting

### Database connection fails

**Check:**
- MySQL is running
- Credentials are correct
- Database exists
- Network connectivity

```bash
# Test MySQL connection
mysql -h host -u user -p database
```

### Encryption key invalid

**Solution:**
```bash
# Regenerate key
python generate_encryption_key.py

# Update .env
ENCRYPTION_KEY=new-key-here

# Restart app
docker-compose restart
```

### CORS errors

**Fix CORS_ORIGINS:**
```bash
# Include all domains that access the API
CORS_ORIGINS=https://app1.com,https://app2.com

# Check browser console for exact origin
```

---

## Next Steps

- [Quick Start Guide](./quick-start.md)
- [Deployment Guide](../operations/deployment.md)
- [Security Best Practices](../architecture/security.md)
