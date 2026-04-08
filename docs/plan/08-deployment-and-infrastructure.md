# 08 - Deployment und Infrastruktur

## Ziel

Produktionsfaehige Trennung von API und Frontend mit stabiler Routing-/TLS-Strategie.

Hinweis: Server-/DNS-/TLS-Operations sind als manuelle Schritte in
`91-manual-deployment-and-operations.md` ausgelagert.

## Zielarchitektur

- Caddy als Reverse Proxy + TLS
- `/api/*` -> FastAPI
- `/*` -> Next.js Node Server
- Dienste via Docker Compose (oder systemd auf eigener Hardware)

## Aenderungen gegenueber aktuellem Stand

- Static Export in Next entfernen (`output: export` und `trailingSlash` entfernen)
- Frontend-Serving im FastAPI-Bootstrap entfernen (`frontend_router`, `mount_frontend`)
- Eigene Container fuer API und Web

## Routing-Pfadabgleich (entschieden)

- Backend erwartet `/api/...` (bereits im Ist-Zustand so implementiert)
- Caddy leitet `/api/*` ohne Prefix-Stripping an FastAPI durch
- `/*` geht an Next.js

## CORS

- **Produktion:** Nicht noetig — Frontend und API laufen hinter Caddy auf gleicher Domain (Same Origin)
- **Lokale Entwicklung:** `CORSMiddleware` fuer `localhost:3000` ↔ `localhost:8000` (bereits vorhanden)
- Kein Wildcard mit Credentials

## Agenten-Outputs (Code/Config)

- Dockerfiles/Caddyfile/Compose-Dateien erstellen oder anpassen
- Routing- und Prefix-Entscheidung in Code/Config abbilden
- CORS-Konfiguration im Backend vorbereiten
- Monitoring-Integrationspunkte (z. B. Sentry SDK) einbauen
