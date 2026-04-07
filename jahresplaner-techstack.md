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

