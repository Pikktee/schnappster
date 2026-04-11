# MCP only — build from repository root: docker build -f mcp-server/Dockerfile .
FROM python:3.13-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app
COPY mcp-server/ ./mcp-server/

WORKDIR /app/mcp-server
RUN uv sync --frozen --no-dev

ENV PATH="/app/mcp-server/.venv/bin:$PATH"

CMD ["schnappster-mcp"]
