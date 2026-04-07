# Jahresplaner — Tech-Stack Übersicht

## Architektur

API-First: Backend und Frontend sind getrennte Layer. Das Frontend ist austauschbar
(Web heute, Mobile App morgen). Alle Clients sprechen gegen dieselbe API.

```
Next.js (Web)         →
React Native (später) →  Hono API  →  SQLite / PostgreSQL
Sonstige Clients      →
```

---

## Backend

| Komponente | Technologie | Begründung |
|---|---|---|
| **Sprache** | TypeScript | Shared Types mit Frontend, kein Typ-Bruch an der API-Grenze |
| **API-Framework** | [Hono](https://hono.dev) | Ultraleichtgewichtig, typsicher, läuft auf Node.js/Bun |
| **Auth** | [Better-Auth](https://better-auth.com) | Self-hosted, E-Mail+Passwort jetzt, SSO später ohne Umbau |
| **ORM** | [Drizzle](https://orm.drizzle.team) | Typsicher, unterstützt SQLite und PostgreSQL identisch |
| **Datenbank** | SQLite → PostgreSQL | SQLite zum Start, PostgreSQL bei Bedarf (ein Import-Wechsel) |
| **E-Mail** | Firmen-SMTP | Passwort-Reset über bestehende Firmen-Infrastruktur |

---

## Frontend

| Komponente | Technologie |
|---|---|
| **Framework** | Next.js (reiner UI-Layer, keine eigene API-Logik) |
| **UI** | shadcn/ui + Tailwind CSS |
| **API-Kommunikation** | fetch gegen Hono-API (`NEXT_PUBLIC_API_URL`) |

---

## Auth — Migrationspfad

```
Phase 1 (jetzt):   E-Mail + Passwort
                   Passwort-Reset via Firmen-SMTP
                   Rollen: Admin, Team-Lead, Mitarbeiter

Phase 2 (später):  + Microsoft 365 / Azure AD SSO    (ein Config-Block)
                   + Google Workspace SSO             (ein Config-Block)
                   Bestehende User bleiben erhalten
```

---

## Deployment

Alles self-hosted, keine externen Dienste.

```yaml
# docker-compose.yml
services:
  api:      # Hono + Better-Auth (Node.js/Bun)
  web:      # Next.js
  # postgres: # optional, wenn SQLite nicht mehr ausreicht
```

Läuft auf jedem Linux-Server oder intern im Firmennetz.

---

## Entscheidungen & Begründungen

**Warum kein Python-Backend?**
Keine Heavy-Processing-Anforderungen (kein Scraping, keine KI-Analyse). TypeScript
ermöglicht Shared Types zwischen API und Frontend — kein manuelles Synchronisieren
von Python-Modellen und TypeScript-Interfaces.

**Warum kein Supabase / PocketBase / Clerk?**
Keine externen oder managed Services gewünscht. Volle Kontrolle, kein Vendor-Lock-in.

**Warum SQLite zum Start?**
Einfaches Deployment (eine Datei), kein DB-Server nötig. Drizzle macht den Wechsel
zu PostgreSQL trivial wenn Concurrent-Write-Last oder Datenmenge es erfordern.

**Warum Better-Auth statt selbst gebautem Auth?**
Passwort-Reset, Session-Management, E-Mail-Verifikation und spätere SSO-Anbindung
(OIDC/OAuth2) sind fertig implementiert und gewartet. Kein externer Service.
