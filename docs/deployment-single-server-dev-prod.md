# Deployment-Strategie: Ein Server fuer Dev und Prod

## Ziel

Dev und Prod kostenguenstig auf **einem** Hetzner-Server betreiben, aber technisch sauber getrennt halten.

## Infrastruktur

- Ein VPS (z. B. CX23 oder CX33, Ubuntu 24.04 LTS)
- Primäre IPv4 aktiv
- Firewall mit eingehend nur `22`, `80`, `443`
- Caddy als Reverse Proxy mit TLS

## Trennung von Dev und Prod

### Domains

- Dev: `dev.<deine-domain>`
- Prod: `app.<deine-domain>` (oder Root-Domain)

### Supabase

- Dev-App nutzt nur `schnappster-dev`
- Prod-App nutzt nur `schnappster-prod`
- Keine Vermischung von Keys oder URLs

### Container/Deployments

- Getrennte Compose-Projekte, z. B.:
  - `docker compose -p schnappster-dev ...`
  - `docker compose -p schnappster-prod ...`
- Getrennte Container-Namen und Ports

### Secrets

- Getrennte Env-Dateien:
  - `.env.dev`
  - `.env.prod`
- Keine gemeinsamen Secret-Werte zwischen Dev und Prod
- Secret/Service-Keys nie im Frontend

## Caddy-Routing (Konzept)

- `dev.<deine-domain>` -> Dev-Container
- `app.<deine-domain>` -> Prod-Container
- TLS fuer beide Hosts aktiv

## Betriebsregeln

- Deployments getrennt ausfuehren (Dev darf Prod nicht beeinflussen)
- Logs und Monitoring pro Umgebung unterscheiden
- Backups regelmaessig testen (Restore pruefen)

## Risiken und spaetere Migration

- Ein Server ist guenstig, aber ein Single Point of Failure.
- Bei steigender Last oder hoeheren Verfuegbarkeitsanforderungen:
  - Prod auf eigenen Server migrieren
  - Dev auf dem kleineren Server belassen
