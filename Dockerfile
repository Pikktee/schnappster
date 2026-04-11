FROM python:3.13-slim

# System-Abhängigkeiten (curl-cffi braucht libcurl + gcc für native Extensions)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    libcurl4-openssl-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Node.js 20 via NodeSource (npm aus apt ist zu alt für Next.js 16)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# uv installieren
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Python-Abhängigkeiten + Frontend-Quellen zusammen kopieren.
# pyproject.toml vor web/ stellt sicher dass ein Version-Bump
# den Frontend-Build-Cache invalidiert.
# mcp-server/ vor uv sync: schnappster-mcp ist path-dependency ([tool.uv.sources]); Paketquelle `mcp-server/app/`.
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