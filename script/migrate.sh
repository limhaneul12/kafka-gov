#!/bin/bash

set -euo pipefail

ALEMBIC_CFG="alembic.ini"

echo "[migrate] Running Alembic migrations using application settings (DB-agnostic)..."
uv run alembic -c "${ALEMBIC_CFG}" upgrade head
echo "[migrate] ✅ migration completed!"