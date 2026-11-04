# syntax=docker/dockerfile:1
# Visa Assistant API (FastAPI)

FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app
# Tesseract OCR (English model) for passport MRZ reading
RUN apt-get update \
    && apt-get install -y --no-install-recommends tesseract-ocr fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --upgrade "pip>=26.2"
COPY pyproject.toml ./
COPY app ./app

# ── test stage: run lint + tests (used by deploy.sh before building the runtime image) ──
FROM base AS test
RUN pip install ".[dev]"
COPY tests ./tests
COPY migrations ./migrations
COPY alembic.ini ./
RUN ruff check . && pytest -q

# ── runtime ──
FROM base AS runtime
RUN pip install . && useradd --system --uid 1001 ivac
COPY alembic.ini ./
COPY migrations ./migrations
USER ivac
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health')" || exit 1
# Apply database migrations, then serve.
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2 --proxy-headers --forwarded-allow-ips '*'"]
