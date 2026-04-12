# 🚀 Deployment Guide

Production deployment guide for Kafka-Gov.

## Quick Deployment

### Development

```bash
docker-compose up -d
```

### Production

```bash
# Run migrations first (the bare Dockerfile image does not auto-run Alembic)
bash script/migrate.sh

# Then start the API container
docker build -t kafka-gov:latest .
docker run -d \
  --name kafka-gov \
  -p 8000:8000 \
  --env-file .env.production \
  --restart unless-stopped \
  kafka-gov:latest
```

---

## Environment Configuration

### Required Variables

```bash
DATABASE_URL=mysql+aiomysql://user:pass@host:3306/kafka_gov
ENCRYPTION_KEY=<generate using generate_encryption_key.py>
ENVIRONMENT=production
LOG_LEVEL=INFO
CORS_ORIGINS=https://kafka-gov.company.com
```

See [`.env.example`](../../.env.example) for all options.

---

## Health Check

```bash
curl https://kafka-gov.company.com/health

# Expected response
{"status": "healthy"}
```

---

## Monitoring

**Logs:**
```bash
docker logs -f kafka-gov
```

**API Docs:**
- Available at `http://your-domain/swagger` in non-production environments only.
- Production disables `/swagger`, `/redoc`, and `/openapi.json`.

---

## Backup & Recovery

```bash
# Backup
mysqldump -u kafka_gov -p kafka_gov > backup_$(date +%Y%m%d).sql

# Restore
mysql -u kafka_gov -p kafka_gov < backup_20250115.sql
```

---

## Next Steps

- [Architecture Overview](../architecture/overview.md)
- [Platform Direction](../features/real-time-data-governance-system.md)
