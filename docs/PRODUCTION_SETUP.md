# 🚀 Production Setup Guide

## Overview

This guide explains how to configure and deploy the current **schema-governance slice** for production environments.

The active runtime assumes:
- a metadata database
- a reachable Schema Registry
- optional object storage for schema artifacts

---

## 1. Environment Variables

### Required Environment Variables

```bash
APP_ENVIRONMENT=production
APP_CORS_ORIGINS=https://yourdomain.com

# Database
DB_HOST=mysql
DB_PORT=3306
DB_USERNAME=user
DB_PASSWORD=CHANGE_ME_STRONG_PASSWORD
DB_DATABASE=kafka_gov

# Schema Registry
SCHEMA_REGISTRY_URL=http://schema-registry:8081

# MinIO
STORAGE_ENDPOINT_URL=http://minio:9000
STORAGE_ACCESS_KEY=CHANGE_ME
STORAGE_SECRET_KEY=CHANGE_ME_STRONG_SECRET

```

---

## 2. Deployment notes

- The current product does **not** require broker-management endpoints in the shipped surface.
- The operational focus is keeping Schema Registry connectivity and schema-governance workflows healthy.
- Run migrations before app startup.

---

## 3. Recommended checks

- verify `/health`
- verify `/api/v1`
- verify Schema Registry connection via `/api/v1/schema-registries/{id}/test`
- verify frontend loads `/schemas`
