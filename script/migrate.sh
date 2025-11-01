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

# Alembic version 테이블 확인 및 불일치 처리
echo "[migrate] 마이그레이션 상태를 확인합니다..."
CURRENT_REVISION=$(MYSQL_PWD="${DB_PASSWORD}" mysql \
    -h "${DB_HOST}" \
    -P "${DB_PORT}" \
    -u "${DB_USER}" \
    -N -s \
    "${DB_NAME}" \
    -e "SELECT version_num FROM alembic_version LIMIT 1" 2>/dev/null || echo "")

if [ -n "${CURRENT_REVISION}" ]; then
    echo "[migrate] 데이터베이스에 기록된 리비전: ${CURRENT_REVISION}"
    
    # 해당 리비전 파일이 존재하는지 확인
    REVISION_EXISTS=$(find "${VERSIONS_DIR}" -name "*${CURRENT_REVISION}*.py" 2>/dev/null | wc -l)
    
    if [ "${REVISION_EXISTS}" -eq "0" ]; then
        echo "[migrate] ⚠️  경고: 리비전 '${CURRENT_REVISION}'에 해당하는 파일을 찾을 수 없습니다."
        echo "[migrate] alembic_version 테이블을 초기화합니다..."
        
        MYSQL_PWD="${DB_PASSWORD}" mysql \
            -h "${DB_HOST}" \
            -P "${DB_PORT}" \
            -u "${DB_USER}" \
            "${DB_NAME}" \
            -e "DELETE FROM alembic_version;"
        
        echo "[migrate] 리비전 초기화 완료. 처음부터 마이그레이션을 시작합니다."
        CURRENT_REVISION=""
    fi
else
    echo "[migrate] 이전 마이그레이션 기록 없음. 새로 시작합니다."
fi

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
    
    # 스키마 변경 사항 확인
    echo "[migrate] 모델 변경 사항을 확인합니다..."
    
    # Alembic으로 pending changes 체크 (dry-run으로 autogenerate)
    TEMP_REVISION=$(mktemp)
    uv run alembic -c "${ALEMBIC_CFG}" revision --autogenerate -m "auto_detect_changes" --sql > "${TEMP_REVISION}" 2>&1 || true
    
    # 생성된 마이그레이션 파일 확인
    NEW_REVISION_FILE=$(VERSIONS_DIR="${VERSIONS_DIR}" python - <<'PY'
import os
import pathlib
import time

versions_dir = pathlib.Path(os.environ["VERSIONS_DIR"])
files = sorted(
    (p for p in versions_dir.glob("*auto_detect_changes*.py") if p.is_file()),
    key=lambda p: p.stat().st_mtime,
    reverse=True,
)
print(files[0].name if files else "")
PY
)
    
    if [ -n "${NEW_REVISION_FILE}" ]; then
        # 마이그레이션 파일 내용 확인 (실제 변경사항이 있는지)
        HAS_CHANGES=$(grep -c "def upgrade()" "${VERSIONS_DIR}/${NEW_REVISION_FILE}" || echo "0")
        
        # upgrade 함수가 비어있지 않은지 확인
        IS_EMPTY=$(grep -A 5 "def upgrade()" "${VERSIONS_DIR}/${NEW_REVISION_FILE}" | grep -c "pass" || echo "0")
        
        if [ "${HAS_CHANGES}" -gt "0" ] && [ "${IS_EMPTY}" -eq "0" ]; then
            echo "[migrate] ✅ 모델 변경 사항 감지! 새로운 마이그레이션 생성됨: ${NEW_REVISION_FILE}"
            REVISION_FILE="${NEW_REVISION_FILE}"
        else
            echo "[migrate] 변경 사항 없음. 자동 생성된 빈 마이그레이션 삭제."
            rm -f "${VERSIONS_DIR}/${NEW_REVISION_FILE}"
        fi
    fi
    
    rm -f "${TEMP_REVISION}"
fi

echo "[migrate] 데이터베이스를 최신 상태로 업그레이드합니다."

# 안전하게 upgrade 실행 (에러 발생 시 재시도)
if ! uv run alembic -c "${ALEMBIC_CFG}" upgrade head; then
    echo "[migrate] ⚠️  업그레이드 실패. 상태를 확인합니다..."
    
    # 현재 head와 DB 버전 비교
    HEAD_REVISION=$(uv run alembic -c "${ALEMBIC_CFG}" heads | awk '{print $1}' | head -n 1)
    echo "[migrate] 최신 리비전: ${HEAD_REVISION}"
    
    # 강제로 head로 stamp (마지막 수단)
    echo "[migrate] 리비전을 강제로 동기화합니다..."
    uv run alembic -c "${ALEMBIC_CFG}" stamp head
    
    echo "[migrate] 동기화 완료. 다시 업그레이드를 시도합니다..."
    uv run alembic -c "${ALEMBIC_CFG}" upgrade head
fi

echo "[migrate] ✅ 마이그레이션 완료!"