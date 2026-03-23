FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Playwright needs OS deps for Chromium; `playwright install --with-deps` will install most of them,
# but it still requires apt to exist (it does) and ca-certificates.
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
  && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt

# Install Django deps + Playwright (Python) and then install Chromium + deps.
RUN pip install --no-cache-dir --retries 10 --timeout 120 -r /app/requirements.txt \
  && pip install --no-cache-dir --retries 10 --timeout 120 playwright==1.52.0 \
  && python -m playwright install --with-deps chromium

COPY . /app

CMD ["bash", "docker/scheduler/entrypoint.sh"]

