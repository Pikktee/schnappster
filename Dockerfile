FROM python:3.13-slim

# System-Abhängigkeiten (curl-cffi braucht libcurl + gcc für native Extensions)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    libcurl4-openssl-dev \
    libssl-dev \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# Node.js 20 via NodeSource (npm aus apt ist zu alt für Next.js 16)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# uv installieren
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Python-Abhängigkeiten zuerst (cached layer bei Code-Änderungen)
COPY pyproject.toml ./
COPY uv.lock* ./
COPY README.md ./
RUN uv sync --frozen --no-dev

# Frontend bauen
COPY pyproject.toml ./    # ← Cache-Buster: invalidiert bei Version-Bump
COPY web/ ./web/
RUN cd web && npm ci && npm run build

# Rest des Projekts
COPY . .

# data/-Verzeichnis anlegen (wird als Volume überschrieben)
RUN mkdir -p /app/data

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]