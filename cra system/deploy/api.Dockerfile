FROM python:3.13.15-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_CACHE_DIR=/tmp/uv-cache \
    HOME=/tmp

RUN groupadd --gid 10001 cra \
    && useradd --uid 10001 --gid cra --create-home --shell /usr/sbin/nologin cra \
    && python -m pip install --no-cache-dir uv==0.12.13

WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
COPY backend ./backend
COPY migrations ./migrations
COPY alembic.ini ./
RUN uv sync --frozen --no-dev \
    && mkdir -p /data/private \
    && chown -R cra:cra /app /data/private

USER 10001:10001
EXPOSE 8000
CMD [".venv/bin/uvicorn", "cra_app.main:app", "--app-dir", "backend", "--host", "0.0.0.0", "--port", "8000"]
