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

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]