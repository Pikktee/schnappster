# 91 - Manuell: Deployment und Betrieb

## Zweck

Diese Aufgaben sind primaer manuelle Ops-Schritte (Hosting, DNS, TLS, Secrets, Betrieb).
Nicht als KI-Agentenplan verwenden.

## Infrastrukturentscheidung

- Zielarchitektur festlegen:
  - Frontend auf Vercel
  - Backend API auf Railway
  - MCP-Server auf Railway (separater Service)
- Domains/Subdomains vorbereiten:
  - `app.<domain>` fuer Frontend (Vercel)
  - `api.<domain>` fuer Backend (Railway)
  - `mcp.<domain>` fuer MCP (Railway)
- DNS-Records fuer alle drei Hosts setzen (CNAME/A je nach Anbieter-Vorgabe)

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

## MCP-Setup (Railway)

- Zweiten Railway-Service fuer MCP aus Monorepo anlegen
- MCP separat vom Backend deployen (eigener Service, eigene Variablen)
- OAuth-/Auth-Variablen und Backend-Base-URL setzen
- Custom Domain `mcp.<domain>` anbinden und HTTPS pruefen

## TLS / Erreichbarkeit

- Fuer alle drei Hosts (`app`, `api`, `mcp`) gueltige HTTPS-Zertifikate pruefen
- CORS auf API fuer erlaubte Frontend-Origin(s) setzen (`app.<domain>`, ggf. Preview-URLs)
- Healthchecks testen:
  - Frontend erreichbar
  - API Endpoint antwortet
  - MCP Endpoint antwortet

## Betrieb

- Update-Prozess festlegen (Git-Push -> Auto-Deploy in Vercel/Railway)
- Deploy-Rollen klar trennen:
  - Frontend-Deploy beeinflusst nicht API/MCP
  - API-Deploy beeinflusst nicht Frontend
- Monitoring aktivieren (z. B. Sentry)
- Logs fuer API und MCP regelmaessig pruefen
- Backup- und Restore-Strategie fuer Postgres/Supabase festlegen
- Incident-Runbook fuer Auth/API-Ausfaelle dokumentieren
