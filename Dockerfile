# syntax=docker/dockerfile:1.6
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Build deps
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps first for layer caching
COPY pyproject.toml ./
RUN pip install --upgrade pip wheel \
 && pip install \
        "fastapi>=0.115" "uvicorn[standard]>=0.32" "jinja2>=3.1" \
        "sqlalchemy>=2.0" "alembic>=1.14" "pydantic>=2.9" \
        "pydantic-settings>=2.6" "python-multipart>=0.0.12" \
        "pandas>=2.2" "openpyxl>=3.1" "xlrd>=2.0" \
        "pyyaml>=6.0" "python-slugify>=8.0"

# App code
COPY app ./app
COPY configs ./configs
COPY exports ./exports
COPY pyproject.toml ./

# Non-root user
RUN useradd -m -u 1000 app && chown -R app:app /app
USER app

# Default DB path inside the container; override via env
ENV DATABASE_URL=sqlite:////data/bcqt.sqlite \
    APP_ENV=prod \
    PORT=8088

VOLUME ["/data"]
EXPOSE 8088

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD curl -fsS "http://127.0.0.1:${PORT}/" || exit 1

# Production server
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --workers 2"]
