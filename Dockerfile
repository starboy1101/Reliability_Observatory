# syntax=docker/dockerfile:1.7
FROM node:22-alpine AS web-build
WORKDIR /build/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim AS runtime
ARG INSTALL_OPTIONAL_INTEGRATIONS=false
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ENVIRONMENT=production \
    STATIC_DIR=/app/static \
    DATABASE_URL=sqlite+aiosqlite:////data/reliability.db \
    PORT=8000 \
    HOME=/tmp/app-home \
    XDG_CACHE_HOME=/tmp/app-home/.cache

RUN addgroup --system app && adduser --system --ingroup app app \
    && mkdir -p /app/backend /app/static /data /tmp/app-home/.cache \
    && chown -R app:app /data /tmp/app-home

WORKDIR /app/backend
COPY backend/requirements.txt /tmp/backend-requirements.txt
RUN pip install --no-cache-dir --requirement /tmp/backend-requirements.txt
COPY backend/ ./
RUN if [ "$INSTALL_OPTIONAL_INTEGRATIONS" = "true" ]; then \
      pip install --no-cache-dir ".[all-integrations]"; \
    fi
COPY --from=web-build /build/frontend/dist /app/static

USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD ["python", "-c", "import os, urllib.request; urllib.request.urlopen(f\"http://127.0.0.1:{os.environ.get('PORT', '8000')}/healthz\", timeout=3).close()"]
CMD ["sh", "-c", "mkdir -p \"$XDG_CACHE_HOME\" && exec uvicorn app.main:app --host 0.0.0.0 --port \"${PORT:-8000}\" --workers 1"]
