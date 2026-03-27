FROM mcr.microsoft.com/playwright/python:v1.58.0-jammy

ARG POSTGRES_DB=""
ARG POSTGRES_USER=""
ARG POSTGRES_PASSWORD=""
ARG POSTGRES_HOST=""
ARG POSTGRES_PORT=""

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    TZ=Europe/Moscow \
    POSTGRES_DB=${POSTGRES_DB} \
    POSTGRES_USER=${POSTGRES_USER} \
    POSTGRES_PASSWORD=${POSTGRES_PASSWORD} \
    POSTGRES_HOST=${POSTGRES_HOST} \
    POSTGRES_PORT=${POSTGRES_PORT}

WORKDIR /app

COPY parser/requirements.txt /app/parser/requirements.txt
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r /app/parser/requirements.txt

COPY . /app

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "from playwright.sync_api import sync_playwright; print('OK')" || exit 1

CMD ["python", "-m", "parser.main", "--headless", "--root", "/app"]
