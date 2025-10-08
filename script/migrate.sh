#!/bin/bash

set -euo pipefail

ALEMBIC_CFG="alembic.ini"
MIGRATIONS_DIR="migrations"
VERSIONS_DIR="${MIGRATIONS_DIR}/versions"

# 마이그레이션 디렉토리가 없으면 초기화
if [ ! -d "${MIGRATIONS_DIR}" ]; then
    echo "[migrate] migrations 디렉토리가 없어 초기화합니다."
    uv run alembic -c "${ALEMBIC_CFG}" init "${MIGRATIONS_DIR}"
fi

DB_HOST=${DB_HOST:-mysql}
DB_PORT=${DB_PORT:-3306}
DB_USER=${DB_USER:-user}
DB_PASSWORD=${DB_PASSWORD:-password}
DB_NAME=${DB_NAME:-kafka_gov}
MYSQL_MAX_RETRIES=${MYSQL_MAX_RETRIES:-30}
MYSQL_RETRY_INTERVAL=${MYSQL_RETRY_INTERVAL:-2}

if ! command -v mysql >/dev/null 2>&1; then
    echo "[migrate] mysql 클라이언트를 찾을 수 없습니다. default-mysql-client를 설치해주세요." >&2
    exit 1
fi

mkdir -p "${VERSIONS_DIR}"

echo "[migrate] MySQL(${DB_HOST}:${DB_PORT}) 연결을 대기합니다."
attempt=1
until MYSQL_PWD="${DB_PASSWORD}" mysql \
    -h "${DB_HOST}" \
    -P "${DB_PORT}" \
    -u "${DB_USER}" \
    --connect-timeout=5 \
    "${DB_NAME}" \
    -e "SELECT 1" >/dev/null 2>&1; do
    if [ "${attempt}" -ge "${MYSQL_MAX_RETRIES}" ]; then
        echo "[migrate] MySQL 연결에 실패했습니다. (시도 횟수: ${attempt})" >&2
        exit 1
    fi
    echo "[migrate] MySQL 응답 대기 중... (${attempt}/${MYSQL_MAX_RETRIES})"
    attempt=$((attempt + 1))
    sleep "${MYSQL_RETRY_INTERVAL}"
done

echo "[migrate] MySQL 연결 확인 완료."

REVISION_FILE=$(VERSIONS_DIR="${VERSIONS_DIR}" python - <<'PY'
import os
import pathlib

versions_dir = pathlib.Path(os.environ["VERSIONS_DIR"])

if not versions_dir.exists():
    print("")
else:
    files = sorted(
        (p for p in versions_dir.glob("*.py") if p.is_file()),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    print(files[0].name if files else "")
PY
)

if [ -z "${REVISION_FILE}" ]; then
    echo "[migrate] 기존 리비전이 없어 자동 생성합니다."
    uv run alembic -c "${ALEMBIC_CFG}" revision --autogenerate -m "init"

    REVISION_FILE=$(VERSIONS_DIR="${VERSIONS_DIR}" python - <<'PY'
import os
import pathlib

versions_dir = pathlib.Path(os.environ["VERSIONS_DIR"])
files = sorted(
    (p for p in versions_dir.glob("*.py") if p.is_file()),
    key=lambda p: p.stat().st_mtime,
    reverse=True,
)
print(files[0].name if files else "")
PY
)

    if [ -z "${REVISION_FILE}" ]; then
        echo "[migrate] 리비전 생성에 실패했습니다." >&2
        exit 1
    fi
else
    echo "[migrate] 기존 리비전 감지: ${REVISION_FILE}"
fi

echo "[migrate] 데이터베이스를 최신 상태로 업그레이드합니다."
uv run alembic -c "${ALEMBIC_CFG}" upgrade head