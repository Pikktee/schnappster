# Go-Live Checkliste (Vercel + Railway)

## Ziel

Sicherer Produktionsstart mit getrenntem Frontend- und Backend-Deployment sowie vorbereiteter Erweiterung fuer einen MCP-Service auf Railway.

## 0) Release-Kandidat einfrieren

- [ ] Letzten Stand in Main mergen
- [ ] `uv run pytest` ist lokal/gruen
- [ ] `cd web && npm run lint` ist lokal/gruen
- [ ] Offene kritische Bugs und bekannte Blocker sind dokumentiert

## 1) Domains und DNS

- [ ] Produktionsdomain fuer Frontend festgelegt (`app.<domain>`)
- [ ] Produktionsdomain fuer API festgelegt (`api.<domain>`)
- [ ] DNS-Eintraege gemaess Vercel/Railway-Anforderungen gesetzt
- [ ] Beide Domains zeigen auf die korrekten Zielsysteme

## 2) Frontend auf Vercel

- [ ] Vercel-Projekt mit Root `web/` angelegt/verknuepft
- [ ] Build- und Startkonfiguration in Vercel erfolgreich
- [ ] Env in Vercel gesetzt: `NEXT_PUBLIC_API_URL=https://api.<domain>`
- [ ] Custom Domain `app.<domain>` verbunden
- [ ] HTTPS fuer `app.<domain>` ist gueltig

## 3) Backend auf Railway (FastAPI)

- [ ] Railway-Service fuer API aus Monorepo angelegt
- [ ] Start-Command auf FastAPI-Entrypoint gesetzt
- [ ] Alle benoetigten ENV-Werte gesetzt (AI, Supabase, Secrets, Runtime)
- [ ] Custom Domain `api.<domain>` verbunden
- [ ] HTTPS fuer `api.<domain>` ist gueltig
- [ ] Persistenz/DB-Setup fuer Produktionsbetrieb verifiziert

## 4) CORS und Security

- [ ] `CORS_ALLOWED_ORIGINS` enthaelt mindestens `https://app.<domain>`
- [ ] Preview-Origin-Freigaben nur in non-prod (optional via Regex)
- [ ] Kein `*` in CORS bei Credentials/Sessions
- [ ] Keine Secrets in `NEXT_PUBLIC_*` Variablen
- [ ] API-Keys/Service-Keys nur serverseitig gesetzt

## 5) Smoke-Tests nach Deploy

- [ ] Frontend unter `https://app.<domain>` erreichbar
- [ ] API-Healthcheck antwortet unter `https://api.<domain>/api/...`
- [ ] Login/Session funktioniert im Browser
- [ ] Mindestens ein API-Call aus Frontend funktioniert ohne CORS-Fehler
- [ ] Scrape-Job startet planmaessig
- [ ] Analyze-Job verarbeitet neue Anzeigen
- [ ] Telegram-Benachrichtigung (falls aktiv) erfolgreich getestet

## 6) Monitoring und Betrieb

- [ ] Fehlertracking aktiv (z. B. Sentry)
- [ ] Railway-Logs fuer API werden beobachtet
- [ ] Vercel-Deployment-Status wird beobachtet
- [ ] Alarmierung/Benachrichtigung fuer Ausfaelle definiert
- [ ] Incident-Runbook fuer API/Auth-Ausfaelle dokumentiert

## 7) Backup und Restore

- [ ] Backup-Strategie fuer produktive Datenbank festgelegt
- [ ] Restore-Test einmal erfolgreich durchgefuehrt
- [ ] Verantwortlichkeiten und Turnus fuer Backups dokumentiert

## 8) MCP-Server Vorbereitung (Railway, naechste Tage)

- [ ] Eigener Railway-Service fuer MCP geplant (nicht im API-Prozess)
- [ ] Eigene ENV/Secrets fuer MCP definiert
- [ ] Auth zwischen API und MCP festgelegt (Token/Secret-Strategie)
- [ ] Entscheidung zu Erreichbarkeit getroffen:
- [ ] - interne Service-Kommunikation oder eigene Domain `mcp.<domain>`
- [ ] Healthcheck und Logging fuer MCP eingeplant
- [ ] Rollback-Strategie fuer MCP-Releases definiert

## 9) Go-/No-Go

- [ ] Abnahme von Frontend, API und Basis-Workflows erfolgt
- [ ] Keine offenen P0/P1 Issues
- [ ] Go-Live Entscheidung dokumentiert (Datum, Verantwortliche)
