# Frontend in eigenem Node-Stage: `npm` per COPY aus dem Node-Image ins Python-Image
# übernimmt oft keine gültigen Symlinks/Pfade (Cannot find module '../lib/cli.js').
FROM node:20-bookworm-slim AS web_build
WORKDIR /app
COPY web/package.json web/package-lock.json ./web/
RUN cd web && npm ci
COPY web/ ./web/
ENV NODE_ENV=production
RUN cd web && npm run build

# Explizit Bookworm — stabil gegen Debian-Wechsel bei `python:3.13-slim`.
FROM python:3.13-slim-bookworm

# System-Abhängigkeiten (curl-cffi braucht libcurl + gcc für native Extensions)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    libcurl4-openssl-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# uv installieren
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Python-Abhängigkeiten + Frontend-Quellen zusammen kopieren.
# pyproject.toml vor web/ stellt sicher dass ein Version-Bump
# den Frontend-Build-Cache invalidiert.
# mcp-server/ vor uv sync: schnappster-mcp ist path-dependency ([tool.uv.sources]); Paket unter `mcp-server/schnappster_mcp/`.
COPY pyproject.toml uv.lock* README.md ./
COPY mcp-server/ ./mcp-server/
RUN uv sync --frozen --no-dev

COPY web/ ./web/
COPY --from=web_build /app/web/out ./web/out/

# Rest des Projekts
COPY . .

# data/-Verzeichnis anlegen (wird als Volume überschrieben)
RUN mkdir -p /app/data

EXPOSE 8000

CMD ["sh", "-c", "uv run uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
