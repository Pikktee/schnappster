# 91 - Manuell: Deployment und Betrieb

## Zweck

Diese Aufgaben sind primaer manuelle Ops-Schritte (Hosting, DNS, TLS, Secrets, Betrieb).
Nicht als KI-Agentenplan verwenden.

## Infrastrukturentscheidung

- Zielarchitektur festlegen:
  - Frontend auf Vercel
  - Backend API auf Railway
- Domains/Subdomains vorbereiten:
  - `app.<domain>` fuer Frontend (Vercel)
  - `api.<domain>` fuer Backend (Railway)
- DNS-Records fuer beide Hosts setzen (CNAME/A je nach Anbieter-Vorgabe)

## Frontend-Setup (Vercel)

- Vercel-Projekt mit `web/` als Root verknuepfen
- Build/Output gemaess bestehendem Frontend-Setup konfigurieren
- Custom Domain `app.<domain>` in Vercel verbinden
- `NEXT_PUBLIC_API_URL` auf `https://api.<domain>` setzen

## Backend-Setup (Railway)

- Railway-Service fuer FastAPI aus Monorepo anlegen
- Start-Command fuer API setzen (entsprechend Projekt-Entrypoint)
- Environment Variablen setzen (u. a. Supabase URL/Keys, AI-Config, App-Secrets)
- Custom Domain `api.<domain>` anbinden und HTTPS pruefen

## TLS / Erreichbarkeit

- Fuer beide Hosts (`app`, `api`) gueltige HTTPS-Zertifikate pruefen
- CORS auf API fuer erlaubte Frontend-Origin(s) setzen (`app.<domain>`, ggf. Preview-URLs)
- Healthchecks testen:
  - Frontend erreichbar
  - API Endpoint antwortet

## Betrieb

- Update-Prozess festlegen (nur Release-Tags deployen)
- Auto-Deploy auf Branch-Push in Vercel und Railway deaktivieren
- GitHub Actions Workflow `.github/workflows/deploy-on-release-tag.yml` verwenden:
  - Trigger: Push von Tags `v*` (z. B. via `uv run release`)
  - Secrets: `VERCEL_TOKEN`, `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID`, `RAILWAY_TOKEN`, `RAILWAY_SERVICE_NAME`, `RAILWAY_ENVIRONMENT_NAME`
- Deploy-Rollen klar trennen:
  - Frontend-Deploy beeinflusst nicht API
  - API-Deploy beeinflusst nicht Frontend
- Monitoring aktivieren (z. B. Sentry)
- Logs fuer API regelmaessig pruefen
- Backup- und Restore-Strategie fuer Postgres/Supabase festlegen
- Incident-Runbook fuer Auth/API-Ausfaelle dokumentieren
