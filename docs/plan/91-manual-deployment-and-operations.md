# 91 - Manuell: Deployment und Betrieb

## Zweck

Diese Aufgaben sind primär manuelle Ops-Schritte (Server, DNS, TLS, Systemdienste).
Nicht als KI-Agentenplan verwenden.

## Infrastrukturentscheidung

- Deploymentziel festlegen: eigener Server (systemd) oder Cloud-VPS (Docker Compose)
- Domain und DNS vorbereiten
- Optional DynDNS einrichten (bei nicht statischer IP)

## Caddy / TLS

- Caddy auf Host installieren oder Container betreiben
- Caddyfile mit API/Web-Routing ausrollen
- TLS-Zertifikate erfolgreich pruefen

## Server-Setup

- Abhaengigkeiten installieren (Docker oder Node/uv/systemd je nach Modell)
- Secrets (`.env`, ggf. `web/.env.local`) sicher hinterlegen
- Dienste starten und beim Boot aktivieren

## Betrieb

- Update-Prozess festlegen (`git pull`, rebuild/restart)
- Monitoring aktivieren (z. B. Sentry)
- Backup- und Restore-Strategie fuer Postgres festlegen
- Incident-Runbook fuer Auth/API-Ausfaelle dokumentieren
