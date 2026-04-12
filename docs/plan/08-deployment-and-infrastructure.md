# 08 - Deployment und Infrastruktur

## Ziel

Produktionsfaehige Trennung von API und Frontend mit stabiler Routing-/TLS-Strategie.

Hinweis: Server-/DNS-/TLS-Operations sind als manuelle Schritte in
`91-manual-deployment-and-operations.md` ausgelagert.

## Zielarchitektur

- Frontend auf Vercel (`app.<domain>`)
- Backend API auf Railway (`api.<domain>`)
- HTTPS/TLS und Domains ueber Vercel/Railway + DNS

## Ist-Stand (Monorepo)

- API und Web sind getrennte Deployments (Vercel + Railway)
- FastAPI liefert nur die REST-API (kein Ausliefern von Next-Build-Artefakten)
- `NEXT_PUBLIC_API_URL` im Frontend auf `https://api.<domain>` setzen

## Routing

- Backend: REST-Pfade an der Wurzel (z. B. `/ads`, `/adsearches`, `/version/`)
- Frontend: Basis-URL `https://api.<domain>` + jeweiliger Pfad (kein globales `/api`-Prefix im FastAPI-Router)

## CORS

- **Produktion:** Notwendig, da Cross-Origin (`app.<domain>` -> `api.<domain>`)
- CORS-Strategie:
  - stabiler Haupt-Origin immer explizit erlauben: `https://app.<domain>`
  - Preview-URLs nur fuer nicht-produktive Umgebungen erlauben (Pattern-Match auf Vercel-Preview-Domains)
  - Produktion bevorzugt ohne Preview-Origin-Freigaben betreiben
- **Lokale Entwicklung:** `CORSMiddleware` fuer `localhost:3000` ↔ `localhost:8000` (bereits vorhanden)
- Kein Wildcard mit Credentials
- Backend-Umsetzung ueber ENV:
  - `CORS_ALLOWED_ORIGINS` (kommagetrennte fixe Origins)
  - optional `CORS_ALLOWED_ORIGIN_REGEX` fuer Preview-Umgebungen

## Agenten-Outputs (Code/Config)

- Vercel/Railway-konforme Build- und Start-Konfigurationen pflegen
- API-Base-URL und Domain-Setup in Frontend/Backend-Konfigurationsdateien abbilden
- CORS-Konfiguration im Backend vorbereiten
- Monitoring-Integrationspunkte (z. B. Sentry SDK) einbauen
