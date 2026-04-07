# Jahresplaner — Tech-Stack und Umsetzungsplan

## Beschreibung

Ein firmeninternes Web-Tool zur Jahresplanung, genutzt von allen Teams und
Abteilungen eines mittelständischen Unternehmens. API-First-Architektur:
das Frontend ist austauschbar (Web jetzt, Mobile App perspektivisch).
Komplett self-hosted, keine externen Managed-Services.

---

## Tech-Stack

### Backend

| Komponente | Technologie | Beschreibung |
|---|---|---|
| **Sprache** | TypeScript | Shared Types zwischen API und Frontend — kein manuelles Synchronisieren von Datenmodellen |
| **API-Framework** | [Hono](https://hono.dev) | Ultraleichtes (~14kb) API-Framework. Läuft auf Node.js, Bun oder Deno. Typsicher, schnell, minimalistisch |
| **Auth** | [Better-Auth](https://better-auth.com) | Self-hosted Auth-Library. E-Mail+Passwort, später SSO (Microsoft/Google) ohne Architekturumbau |
| **ORM** | [Drizzle](https://orm.drizzle.team) | Typsicheres ORM. Unterstützt SQLite und PostgreSQL mit identischer API — DB-Wechsel ist ein Import-Austausch |
| **Datenbank** | SQLite → PostgreSQL | SQLite zum Start (einfach, keine Server-Infrastruktur), PostgreSQL bei wachsender Last |
| **E-Mail** | Firmen-SMTP | Passwort-Reset und Benachrichtigungen über bestehende Firmen-Mailinfrastruktur |
| **Tests** | [Vitest](https://vitest.dev) | Test-Runner, schneller als Jest, natives TypeScript |

<details>
<summary>Zukunftssicherheit der Kernbibliotheken</summary>

| Bibliothek | Stars | Backing | Genutzt von |
|---|---|---|---|
| **Hono** | 25k+ | Cloudflare (Entwickler in Vollzeit angestellt) | Cloudflare intern (D1, KV, Queues) |
| **Better-Auth** | 27k+ | Y Combinator, $5M Seed (Peak XV / Sequoia) | Dokploy, Folo, Zero; empfohlen von Next.js, Nuxt, Astro |
| **Drizzle** | 33k+ | PlanetScale (Kernteam übernommen, 2026) | Replit, Sentry, Figma, Databricks; Astro DB basiert auf Drizzle |
| **Vitest** | 16k+ | Vercel, Chromatic (Sponsoring) | De-facto-Standard im Vite-Ökosystem, 2–5x schneller als Jest |

</details>

### Frontend

| Komponente | Technologie | Beschreibung |
|---|---|---|
| **Framework** | [Next.js](https://nextjs.org) | Reiner UI-Layer, keine eigene API-Logik. Austauschbar ohne API-Änderungen |
| **API-Anbindung** | fetch / SWR | Kommunikation gegen Hono-API via `NEXT_PUBLIC_API_URL` |
| **Tests** | [React Testing Library](https://testing-library.com) | Komponententests, nutzerzentriert |

---

## Repo-Struktur: Monorepo

```
jahresplaner/
  api/              ← Hono + Better-Auth + Drizzle
    src/
      routes/       ← HTTP-Handler (dünn)
      domain/       ← Geschäftslogik-Klassen
      db/           ← Drizzle-Schema, Migrations
      middleware/    ← Auth, Error-Handling
      lib/          ← Hilfsfunktionen, SMTP
    tests/
  web/              ← Next.js (reiner UI-Layer)
    app/            ← App Router, Seiten + Layouts
    components/     ← UI-Primitives + Feature-Komponenten
    lib/            ← API-Client, Auth-Client
    hooks/          ← useVacations(), useTeam(), etc.
  shared/           ← API-Vertrag (nur Typen + Zod-Schemas)
    types/
    schemas/
  mobile/           ← React Native (perspektivisch)
  package.json      ← Workspace-Root (workspaces: ["api", "web", "shared"])
  docker-compose.yml
```

Alle Packages importieren Typen aus `shared/` via `@jahresplaner/shared`.
Frontend, API und perspektivisch Mobile App nutzen dieselben Typen.

---

## Hinweise für Vibe-Coding

### Was hervorragend funktioniert

- **Next.js, TypeScript** — Claude kennt diese Stacks sehr gut
- **Drizzle** — Schema-Definitionen und Queries sind vorhersagbar
- **PostgreSQL / SQLite** — seit Jahrzehnten stabil

### Worauf man achten muss

- **Better-Auth** — jung (2024), Claude kennt die Library nur begrenzt. Wird möglicherweise veraltete API-Patterns vorschlagen oder auf Auth.js-Muster zurückfallen.
- **Hono** — besser als Better-Auth was Claude-Wissen angeht, aber bei neueren Features unsicher.

Für beide Libraries **Context7 nutzen** (siehe unten) — damit arbeitet Claude mit aktueller Doku statt mit veraltetem Trainingswissen.

### Context7 MCP-Server einrichten

Kompensiert Wissenslücken bei neuen Libraries. Claude holt gezielt aktuelle Doku
(nicht alles, nur was relevant ist):

```json
// .claude/settings.json
{
  "mcpServers": {
    "context7": {
      "command": "npx",
      "args": ["-y", "@upstash/context7-mcp"]
    }
  }
}
```

### CLAUDE.md erweitern

Die bestehende CLAUDE.md im Repo-Root um folgende Abschnitte erweitern.
Diese steuern Codequalität, Architektur und Teststrategie — ohne sie
generiert Claude oft Code ohne Tests und mit inkonsistentem Stil.

<details>
<summary>Vollständige CLAUDE.md anzeigen</summary>

```markdown
# CLAUDE.md

## Projekt
Firmeninterner Jahresplaner. API-First Monorepo mit Hono (API), Next.js (Web), shared (Typen).

## Befehle
- `npm run dev` — startet API + Web parallel
- `npm test` — alle Tests (Vitest + React Testing Library)
- `npm run lint` — Linting
- `npm run build` — Production Build

## MCP
Nutze immer context7 wenn du Code für Better-Auth, Hono oder Drizzle generierst.

## Architektur
- Geschäftsregeln in eigene Klassen in `api/src/domain/` — ohne DB- oder HTTP-Abhängigkeit
- Faustregel: eine Regel → Funktion; mehrere zusammengehörige Regeln → Klasse
- Routes sind dünn: validieren, Domain aufrufen, Response zurückgeben
- Shared Types in `shared/` — keine Typ-Duplikate zwischen api und web

## Tests
- Jede neue Domain-Klasse braucht Unit-Tests (Vitest)
- Jede neue Route braucht mindestens einen Happy-Path-Integrationstest (Hono Test-Client)
- Tests VOR der Implementierung schreiben wenn die Anforderung klar ist
- `npm test` muss vor jedem Commit grün sein
- Teste Verhalten, nicht Interna — keine gemockten Implementierungsdetails

## Code-Stil
- Sprechende Namen, keine Abkürzungen (`getActiveTeamMembers`, nicht `getATM`)
- Funktionen maximal 20 Zeilen
- Maximal 2 Ebenen Einrückung (kein tief verschachteltes if/for/try)
- Early Return statt verschachtelter if-Blöcke
- Keine auskommentierten Code-Blöcke, keine Magic Numbers
- Kommentare nur WARUM, nicht WAS — kein Kommentar ist besser als ein trivialer

## TypeScript
- `strict: true` — immer
- Kein `any` (→ `unknown` + Type Guards), kein `as` (→ Type Guards oder Zod)
- `type` statt `interface`
- Keine Enums — Union-Typen: `type Role = 'admin' | 'team-lead' | 'user'`
- Zod-Schema als Single Source of Truth: `type Vacation = z.infer<typeof vacationSchema>`
- Explizite Return-Typen nur bei exportierten Funktionen
- Discriminated Unions statt Exceptions: `{ ok: true, data } | { ok: false, reason }`
- Typ-Imports markieren: `import type { Vacation } from ...`
- Import-Sortierung: extern → intern → relativ
```

</details>

---

## Begründungen und Vergleiche

### Warum TypeScript statt Python (FastAPI)?

| Kriterium | TypeScript (Hono) | Python (FastAPI) |
|---|---|---|
| **Shared Types** | ✅ ein Typ für API + Frontend | ❌ doppelte Typen (Python + TS) |
| **KI / Scraping** | ❌ schwächer | ✅ klare Stärke |
| **API-Entwicklung** | ✅ gleichwertig | ✅ gleichwertig |
| **Lernkurve** | niedrig bei JS-Kenntnis | niedrig bei Python-Kenntnis |

**Entscheidung TypeScript** weil: keine Heavy-Processing-Anforderungen (kein Scraping,
keine KI-Analyse). Der Hauptvorteil ist die durchgängige Typsicherheit — ein Typ-
Fehler im API-Response wird direkt im Frontend-Code sichtbar, ohne manuelle Synchronisation.

### Warum Hono statt Express / Fastify / Next.js Route Handlers?

| Kriterium | Hono | Express | Fastify | Next.js Route Handlers |
|---|---|---|---|---|
| **Gewicht** | ~14kb | ~200kb | ~100kb | Teil von Next.js |
| **TypeScript** | ✅ nativ | ⚠️ nachgerüstet | ⚠️ nachgerüstet | ✅ |
| **API-First** | ✅ dafür gebaut | ✅ | ✅ | ⚠️ mit Next.js gekoppelt |
| **Better-Auth** | ✅ native Integration | ⚠️ Adapter | ⚠️ Adapter | ✅ |
| **Frontend-unabhängig** | ✅ eigenständig | ✅ | ✅ | ❌ Next.js gebunden |
| **Verbreitung** | wachsend | sehr hoch | hoch | hoch |

**Entscheidung Hono** weil: echte API-Trennung vom Frontend (Handy-App später möglich),
ultraleicht, native Better-Auth-Integration. Express ist veraltet im API-Design,
Next.js Route Handlers koppeln API ans Frontend.

### Warum Better-Auth statt Auth.js / Clerk / Logto / Supabase Auth?

| Kriterium | Better-Auth | Auth.js v5 | Clerk | Logto | Supabase Auth |
|---|---|---|---|---|---|
| **Self-hosted** | ✅ | ✅ | ❌ managed only | ✅ | ✅ (Docker-Stack) |
| **Hono-Support** | ✅ nativ | ⚠️ Wrapper nötig | ❌ JWT-Validierung | ❌ JWT-Validierung | ❌ JWT-Validierung |
| **E-Mail+Passwort** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **SSO später** | ✅ ein Config-Block | ✅ | ✅ | ✅ | ✅ |
| **Eigenständigkeit** | ✅ Framework-agnostisch | ⚠️ Next.js-lastig | ❌ externer Dienst | ⚠️ eigener Container | ⚠️ ganzer Supabase-Stack |
| **Reife** | jung (2024), YC-backed | etabliert | etabliert | mittel | etabliert |
| **Vendor-Lock-in** | keiner | keiner | hoch | niedrig | mittel |

**Entscheidung Better-Auth** weil: einzige Library mit nativer Hono-Integration,
self-hosted ohne extra Container, SSO später ohne Umbau. Auth.js wäre die Alternative
wenn statt Hono Next.js Route Handlers als API-Layer genutzt würden. Clerk und
Supabase Auth scheiden aus wegen Managed-Service bzw. Overhead.

### Warum Drizzle statt Prisma?

| Kriterium | Drizzle | Prisma |
|---|---|---|
| **SQLite + PostgreSQL** | ✅ identische API | ✅ aber unterschiedliche Provider-Syntax |
| **Bundle-Größe** | leicht | schwer (Engine-Binary) |
| **SQL-Nähe** | ✅ SQL-ähnliche Syntax | eigene Query-Sprache |
| **TypeScript-Integration** | ✅ Schema = TypeScript | Schema-Datei → generierte Typen |
| **Migrations** | leicht (drizzle-kit) | gut (prisma migrate) |
| **Verbreitung** | wachsend | höher |

**Entscheidung Drizzle** weil: leichter, DB-Wechsel (SQLite → Postgres) ist trivial,
Typ-Definitionen direkt in TypeScript (kein separates Schema-File + Code-Generation).

### Warum kein PocketBase?

PocketBase klingt verlockend (ein Binary, Auth eingebaut), aber: es generiert die API
automatisch aus dem DB-Schema. Das bedeutet keine eigene Business-Logik-Schicht, keine
Kontrolle über API-Design, und Sackgasse bei komplexeren Anforderungen. Für ein
langlebiges Firmentool nicht geeignet.

### Warum kein Supabase (für den Jahresplaner)?

Supabase ist ein ganzer Service-Stack (~10 Docker-Container). Für ein firmeninternes Tool
ohne SaaS-Ambitionen ist das Overkill. Der Jahresplaner braucht keine RLS, kein
Realtime, kein Storage — nur Auth + DB + API.

### Warum Monorepo?

- Shared Types zwischen API und Frontend — der Hauptvorteil von TypeScript geht
  verloren wenn die Typen in getrennten Repos liegen
- Vibe-Coding: Claude muss API und Frontend gleichzeitig sehen um konsistente
  Änderungen zu machen. Bei getrennten Repos fehlt der Kontext
- Eine Änderung, ein Commit — API-Endpoint + Frontend-Call + Typen gehören zusammen
- Kein Versions-Chaos zwischen Frontend und API

Separate Repos lohnen sich erst wenn getrennte Teams unabhängig deployen müssen.

---

## Umsetzungsreihenfolge

### Phase 1: Monorepo + API-Grundgerüst

1. Workspace-Root initialisieren: `package.json` mit `workspaces: ["api", "web", "shared"]`
2. `shared/` anlegen: `package.json` mit Name `@jahresplaner/shared`, `types/` und `schemas/` Verzeichnisse
3. `api/` anlegen: Hono-Server in `api/src/index.ts`, Drizzle mit SQLite in `api/src/db/`
4. Drizzle-Schema definieren in `api/src/db/schema.ts` (Teams, Users, Planungseinträge)
5. Erste Route erstellen: `GET /api/health` → `{ status: "ok" }`
6. Vitest einrichten in `api/`, erster Test für Health-Route
7. `npm run dev` Skript im Root das `api` dev-server startet

### Phase 2: Auth

1. Better-Auth in `api/` integrieren: `npm install better-auth` in `api/`
2. Better-Auth konfigurieren in `api/src/lib/auth.ts`:
   - E-Mail + Passwort aktivieren
   - Drizzle-Adapter anbinden
   - SMTP für Passwort-Reset konfigurieren
3. Auth-Middleware in `api/src/middleware/auth.ts`:
   - `requireAuth` — eingeloggter User
   - `requireRole('admin')` — Rollenprüfung
4. Auth-Routen testen: Registration, Login, Logout, Passwort-Reset

### Phase 3: Frontend

1. Next.js in `web/` initialisieren: `npx create-next-app@latest` mit App Router
2. API-Proxy konfigurieren in `web/next.config.ts`: `/api` → `http://localhost:4000`
3. Auth-Client in `web/lib/auth.ts`: Better-Auth Client-SDK
4. Login-Seite in `web/app/(auth)/login/page.tsx`
5. App-Layout in `web/app/(app)/layout.tsx`: Navigation, User-Menü, Logout
6. Typsicherer API-Client in `web/lib/api-client.ts`: importiert Typen aus `@jahresplaner/shared`
7. `npm run dev` Skript im Root erweitern: `api` + `web` parallel starten

### Phase 4: Rollen + Geschäftslogik

1. Rollen implementieren: Admin, Team-Lead, Mitarbeiter
2. Domain-Klassen in `api/src/domain/` mit Unit-Tests in `api/tests/domain/`
3. Routes in `api/src/routes/` — dünn, nur Verdrahtung zu Domain-Klassen

### Phase 5: Features

Planungsfunktionen, Team-Zuordnungen, Kalender-Views — je nach fachlichen Anforderungen.

### Phase 6: Deployment

1. Dockerfile je für `api/` und `web/`
2. `docker-compose.yml` im Root mit Caddy als Reverse Proxy
3. Caddy leitet `/api/*` an Hono (:4000), alles andere an Next.js (:3000)

**Lokale Entwicklung:** Kein Docker nötig. `npm run dev` im Root startet beide
Dev-Server parallel (Hono + Next.js) mit Hot Reload. Next.js proxied `/api`
automatisch an den lokalen Hono-Server.
