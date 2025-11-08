# Use Python 3.12 slim image
FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    curl default-mysql-client \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_CACHE_DIR=/tmp/uv-cache

COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/tmp/uv-cache uv sync --frozen --no-dev

# 앱 코드 및 설정 복사
COPY app/ ./app/
# COPY static/ ./static/
COPY script/ ./script/
COPY alembic.ini ./
# ★ 여기가 포인트: 레포의 migrations 폴더를 그대로 이미지에 포함
COPY migrations/ ./migrations/

# 권한/사용자 설정
RUN useradd --create-home --shell /bin/bash app && chown -R app:app /app
USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 멀티프로세스 실행 (Gunicorn + UvicornWorker)
# --workers: CPU 코어 기반 (2개 권장, 환경변수로 조정 가능)
# --worker-class: Uvicorn의 비동기 워커 사용
# --timeout: 요청 타임아웃 (120초)
# --graceful-timeout: Graceful shutdown 시간 (30초)
# --keep-alive: Keep-Alive 연결 유지 시간 (5초)
CMD ["uv", "run", "gunicorn", "app.main:app", \
     "-k", "uvicorn.workers.UvicornWorker", \
     "--workers", "2", \
     "--bind", "0.0.0.0:8000", \
     "--timeout", "120", \
     "--graceful-timeout", "30", \
     "--keep-alive", "5", \
     "--log-level", "info", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]