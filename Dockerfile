# API-Image (Railway/Docker): nur Python, kein Next.js-Build.
FROM python:3.13-slim-bookworm

# System-Abhängigkeiten (curl-cffi braucht libcurl + gcc für native Extensions)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    libcurl4-openssl-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# mcp-server/ vor uv sync: schnappster-mcp ist path-dependency ([tool.uv.sources]).
COPY pyproject.toml uv.lock* README.md ./
COPY mcp-server/ ./mcp-server/
RUN uv sync --frozen --no-dev

COPY . .

EXPOSE 8000

CMD ["sh", "-c", "uv run uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
