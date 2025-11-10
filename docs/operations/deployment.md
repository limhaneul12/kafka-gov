# 🚀 Deployment Guide

Production deployment guide for Kafka-Gov.

## Quick Deployment

### Development

```bash
docker-compose up -d
```

### Production

```bash
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
{"status": "healthy", "database": "connected", "version": "1.0.0"}
```

---

## Monitoring

**Logs:**
```bash
docker logs -f kafka-gov
```

**Metrics:**
- Available at `/metrics` (Prometheus format)
- API docs: http://your-domain/docs

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

- [Kubernetes Deployment](./kubernetes.md)
- [Production Checklist](./production-checklist.md)
- [Monitoring Guide](./monitoring.md)
