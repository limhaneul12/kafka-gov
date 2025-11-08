# 🚀 Production Setup Guide

## Overview

This guide explains how to configure and deploy the Kafka Governance project for production environments.

---

## 1. Environment Variables

### Required Environment Variables

Create a `.env` file and configure the following variables:

```bash
# Environment Settings
APP_ENVIRONMENT=production  # development, staging, production

# CORS Configuration (replace with production domain)
APP_CORS_ORIGINS=https://yourdomain.com,https://admin.yourdomain.com

# Database
DB_HOST=mysql
DB_PORT=3306
DB_USERNAME=user
DB_PASSWORD=CHANGE_ME_STRONG_PASSWORD
DB_DATABASE=kafka_gov

# Kafka
KAFKA_BOOTSTRAP_SERVERS=kafka1:9092,kafka2:9092,kafka3:9092
SCHEMA_REGISTRY_URL=http://schema-registry:8081

# MinIO
STORAGE_ENDPOINT_URL=http://minio:9000
STORAGE_ACCESS_KEY=CHANGE_ME
STORAGE_SECRET_KEY=CHANGE_ME_STRONG_SECRET

# Redis
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
```

### Optional Environment Variables

```bash
# API Documentation Basic Auth (for development/staging)
DOCS_AUTH_USER=admin
DOCS_AUTH_PASSWORD=CHANGE_ME_SECURE_PASSWORD
```

---

## 2. Security Configuration

### 2.1 API Documentation Protection

**Production Environment:**
- When `APP_ENVIRONMENT=production`, `/docs`, `/redoc`, `/openapi.json` are automatically disabled
- FastAPI doesn't create these endpoints, so nginx returns 404

**Development/Staging Environment:**
- Enable nginx Basic Auth (optional)
- Uncomment lines 167-171 in `nginx/nginx.conf`:
  ```nginx
  auth_basic "API Documentation";
  auth_basic_user_file /etc/nginx/.htpasswd;
  ```

### 2.2 CORS Whitelist

**Development Environment:**
```bash
APP_CORS_ORIGINS=http://localhost:3000,http://localhost:5173,http://localhost:80
```

**Production Environment:**
```bash
APP_CORS_ORIGINS=https://yourdomain.com
```

**Wildcard (Not Recommended):**
```bash
APP_CORS_ORIGINS=*
```

### 2.3 nginx CORS Configuration

To allow production domains, modify lines 7-14 in `nginx/nginx.conf`:

```nginx
map $http_origin $cors_origin {
    default "";
    "~^https?://localhost(:[0-9]+)?$" $http_origin;
    "https://yourdomain.com" $http_origin;  # Add your domain
    "https://admin.yourdomain.com" $http_origin;  # Add admin domain
}
```

---

## 3. Multi-Process Configuration

### 3.1 Gunicorn Worker Count Adjustment

Default: **2 workers**

Adjust based on CPU cores:
```dockerfile
# Dockerfile lines 43-52
CMD ["uv", "run", "gunicorn", "app.main:app", \
     "--workers", "4", \  # Adjust based on CPU cores
     ...
]
```

Recommended formula: `workers = min(2 * CPU_CORES, 4-6)`

### 3.2 docker-compose Resource Limits

```yaml
app:
  deploy:
    resources:
      limits:
        cpus: '2.0'
        memory: 2G
      reservations:
        cpus: '1.0'
        memory: 1G
```

---

## 4. nginx Optimization

### 4.1 Static File Caching

Current configuration:
- **JS/CSS/Images**: 1-day cache (`immutable`)
- **HTML**: 5-minute cache (`must-revalidate`)

Adjustable in `nginx/nginx.conf` lines 202-219 if needed

### 4.2 Rate Limiting (Optional)

Add rate limiting for DDoS protection (top of nginx.conf):

```nginx
http {
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=100r/s;
    
    server {
        location /api/ {
            limit_req zone=api_limit burst=20 nodelay;
            ...
        }
    }
}
```

---

## 5. Deployment Checklist

### Pre-Deployment Verification

- [ ] Change all passwords in `.env` file
- [ ] Set `APP_ENVIRONMENT=production`
- [ ] Configure `APP_CORS_ORIGINS` with production domain(s)
- [ ] Add production domain(s) to nginx `$cors_origin` map
- [ ] Adjust Gunicorn workers count based on CPU
- [ ] Configure database backup
- [ ] Set up log collection/monitoring
- [ ] Configure SSL/TLS certificates (add HTTPS to nginx)

### Deployment Commands

```bash
# Build and run
docker-compose up -d --build

# Check logs
docker-compose logs -f app

# Verify health check
curl http://localhost/health
curl http://localhost/api
```

---

## 6. HTTPS Configuration (Recommended)

### Using Let's Encrypt + Certbot

1. **Add Certbot Container** (`docker-compose.yml`):
```yaml
certbot:
  image: certbot/certbot
  volumes:
    - ./certbot/conf:/etc/letsencrypt
    - ./certbot/www:/var/www/certbot
  entrypoint: "/bin/sh -c 'trap exit TERM; while :; do certbot renew; sleep 12h & wait $${!}; done;'"
```

2. **nginx HTTPS Configuration** (add to `nginx/nginx.conf`):
```nginx
server {
    listen 443 ssl http2;
    server_name yourdomain.com;
    
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    
    # SSL Configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    
    # HSTS
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    
    # Other location blocks...
}

# HTTP -> HTTPS redirect
server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}
```

---

## 7. Monitoring & Logging

### 7.1 Structured Logging (Future Enhancement)

Currently supports basic logging only. JSON logging + Request ID will be added in the future.

### 7.2 Prometheus Metrics (Optional)

Since `prometheus-client` is already installed, you can add a `/metrics` endpoint if needed.

### 7.3 Log Collection

nginx logs are stored in JSON format at `/var/log/nginx`:
```json
{
  "time": "2025-01-01T00:00:00+00:00",
  "remote_addr": "1.2.3.4",
  "request_method": "GET",
  "request_uri": "/api/v1/topics",
  "status": 200,
  "request_time": 0.123,
  "upstream_response_time": "0.120"
}
```

---

## 8. Troubleshooting

### Issue: CORS Error
**Cause**: Frontend domain not registered in `APP_CORS_ORIGINS`
**Solution**: Check environment variables and nginx `$cors_origin` map

### Issue: API Documentation Not Accessible (404)
**Cause**: Automatically disabled in production environment
**Solution**: Change to `APP_ENVIRONMENT=development` (for development only)

### Issue: Multi-Process Not Working
**Cause**: Gunicorn not used in Dockerfile
**Solution**: Check Dockerfile lines 43-52, verify `gunicorn` command usage

### Issue: Slow Static File Loading
**Cause**: Caching not applied
**Solution**: Check `X-Cache-Status` header in browser developer tools

---

## 9. References

- [FastAPI Production Checklist](./fastapi_production_checklist.md)
- [Docker Compose Reference](https://docs.docker.com/compose/)
- [Gunicorn Settings](https://docs.gunicorn.org/en/stable/settings.html)
- [nginx Best Practices](https://nginx.org/en/docs/)

---

## License

This project is open-source and welcomes community contributions! 
