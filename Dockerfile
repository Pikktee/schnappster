# Explizit Bookworm: `python:3.13-slim` folgt Debian-Default (z. B. Trixie) — NodeSource/apt
# für Node 20 bricht dort häufig; offizielles Node-Image + passende Python-Basis bleiben stabil.
FROM node:20-bookworm-slim AS node_upstream

FROM python:3.13-slim-bookworm

# System-Abhängigkeiten (curl-cffi braucht libcurl + gcc für native Extensions)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    libcurl4-openssl-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Node 20 + npm aus offiziellem Image (kein NodeSource — zu fragil bei neuen Debian-Releases)
COPY --from=node_upstream /usr/local/bin/node /usr/local/bin/node
COPY --from=node_upstream /usr/local/bin/npm /usr/local/bin/npm
COPY --from=node_upstream /usr/local/bin/npx /usr/local/bin/npx
COPY --from=node_upstream /usr/local/lib/node_modules /usr/local/lib/node_modules

# uv installieren
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Python-Abhängigkeiten + Frontend-Quellen zusammen kopieren.
# pyproject.toml vor web/ stellt sicher dass ein Version-Bump
# den Frontend-Build-Cache invalidiert.
# mcp-server/ vor uv sync: schnappster-mcp ist path-dependency ([tool.uv.sources]); Code unter `mcp-server/app/`, Symlink `schnappster_mcp` → `app`.
COPY pyproject.toml uv.lock* README.md ./
COPY mcp-server/ ./mcp-server/
RUN uv sync --frozen --no-dev

COPY web/ ./web/
RUN cd web && npm ci && npm run build

# Rest des Projekts
COPY . .

# data/-Verzeichnis anlegen (wird als Volume überschrieben)
RUN mkdir -p /app/data

EXPOSE 8000

CMD ["sh", "-c", "uv run uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]