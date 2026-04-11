# Release- und Tag-Deploy-Ueberblick

## Ziel

Deployments sollen **nur** bei einem echten Release passieren, nicht bei jedem Push auf `main`.

## Kurz erklaert: Was sind GitHub Workflows?

GitHub Workflows (GitHub Actions) sind automatisierte Ablaeufe im Repository.
Sie reagieren auf Ereignisse wie Pushes, Pull Requests oder Tag-Pushes.

In diesem Projekt verwenden wir einen Workflow, der nur auf Release-Tags (`v*`) reagiert.

## Was wir hier tun

- Branch-Pushes (z. B. auf `main`) sollen **kein** Deployment mehr ausloesen.
- Ein Deployment soll nur starten, wenn ein Release-Tag gepusht wird (z. B. `v1.2.3`).
- Der Workflow `.github/workflows/deploy-on-release-tag.yml` triggert dann:
  - einen Vercel Deploy per Vercel CLI
  - einen Railway Deploy per Railway CLI (API-Backend)
  - einen zweiten Railway Deploy fuer den **MCP-Server** (eigener Service, Image aus `mcp-server/Dockerfile`)

## Ablauf fuer das Team

1. Normal entwickeln und auf `main` pushen
2. Kein automatisches Deployment
3. Wenn ein Release gewuenscht ist: `uv run release [major|minor|patch]`
4. Das Script erstellt und pusht einen neuen Tag (`vX.Y.Z`)
5. GitHub Workflow startet durch den Tag-Push
6. Workflow deployed Vercel per CLI und deployed beide Railway-Services per CLI
7. Vercel und Railway deployen die neue Version

## Einmalige Einrichtung

### 1) GitHub

Repository: `Settings` -> `Secrets and variables` -> `Actions`

Diese Secrets anlegen:

- `VERCEL_TOKEN`
- `VERCEL_ORG_ID`
- `VERCEL_PROJECT_ID`
- `RAILWAY_TOKEN`
- `RAILWAY_SERVICE_NAME` (FastAPI-Backend)
- `RAILWAY_MCP_SERVICE_NAME` (MCP-Server, eigener Railway-Service)
- `RAILWAY_ENVIRONMENT_NAME`

Diese enthalten Vercel- und Railway-CLI-Zugangsdaten sowie Ziel-Service/-Environment.

### 2) Vercel

- Git-Integration optional trennen (`Settings` -> `Git` -> `Disconnect`)
- In Vercel Account Token erstellen und als `VERCEL_TOKEN` in GitHub speichern
- `VERCEL_ORG_ID` und `VERCEL_PROJECT_ID` aus dem Vercel-Projekt verwenden und in GitHub speichern
- Auto-Deploy bei Push auf `main` deaktivieren bzw. durch Trennen der Git-Integration ausschliessen

### 3) Railway

- Project Token erstellen und als `RAILWAY_TOKEN` in GitHub speichern
- Service-Name des Backends als `RAILWAY_SERVICE_NAME` in GitHub speichern (z. B. `backend`)
- Service-Name des MCP-Servers als `RAILWAY_MCP_SERVICE_NAME` speichern (wie im Railway-Dashboard, z. B. `mcp-server`)
- Environment-Name als `RAILWAY_ENVIRONMENT_NAME` in GitHub speichern (z. B. `production`)
- Auto-Deploy bei Push auf `main` deaktivieren

## Relevante Datei im Repo

- `.github/workflows/deploy-on-release-tag.yml`

Trigger:

- `push` auf Tags `v*`

## Erwartetes Verhalten danach

- `git push origin main` -> kein Deploy
- `uv run release patch` -> Tag `vX.Y.Z` -> Deploy wird ausgeloest

## Kurzer Test nach Setup

1. Sicherstellen, dass alle sieben Secrets in GitHub gesetzt sind (Vercel drei, Railway vier inkl. `RAILWAY_MCP_SERVICE_NAME`)
2. Test-Release erstellen: `uv run release patch`
3. In GitHub unter `Actions` pruefen, ob der Workflow laeuft
4. In Vercel/Railway pruefen, ob jeweils ein Deployment gestartet wurde
