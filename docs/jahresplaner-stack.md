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
| **Auth** | [Better-Auth](https://better-auth.com) | Self-hosted Auth-Library. E-Mail+Passwort, später SSO (Microsoft/Google) ohne Architekturumbau. YC-backed, $5M Funding |
| **ORM** | [Drizzle](https://orm.drizzle.team) | Typsicheres ORM. Unterstützt SQLite und PostgreSQL mit identischer API — DB-Wechsel ist ein Import-Austausch |
| **Datenbank** | SQLite → PostgreSQL | SQLite zum Start (einfach, keine Server-Infrastruktur), PostgreSQL bei wachsender Last |
| **E-Mail** | Firmen-SMTP | Passwort-Reset und Benachrichtigungen über bestehende Firmen-Mailinfrastruktur |
| **Tests** | [Vitest](https://vitest.dev) | Test-Runner, schneller als Jest, natives TypeScript |

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

## Geschäftslogik isolieren

Geschäftsregeln gehören weder in Routes noch in DB-Queries — sie werden in eigenen
Klassen gekapselt. Reine Funktionen/Klassen ohne DB- oder HTTP-Abhängigkeit,
testbar mit simplen Objekten.

**Faustregel:** Eine einzelne Regel → eigene Funktion. Mehrere zusammengehörige
Regeln auf denselben Daten → eigene Klasse.

---

## Tests

### Strategie nach Schicht

| Schicht | Testtyp | Tool | Aufwand |
|---|---|---|---|
| `domain/` | Unit-Tests | Vitest | kein Setup, schnell, höchste Abdeckung |
| `routes/` | Integrationstests | Vitest + Hono Test-Client | kein externer Server nötig |
| `web/` | Komponententests | React Testing Library | isolierte UI-Tests |

**Domain-Tests** sind der größte Hebel — reine Geschäftslogik ohne DB oder HTTP:

```typescript
// api/tests/domain/vacation-policy.test.ts
describe('VacationPolicy', () => {
  it('lehnt ab wenn >30% des Teams abwesend', () => {
    const team = { members: ['a', 'b', 'c'] }
    const existing = [{ userId: 'a', from: '2026-07-01', to: '2026-07-14' }]
    const policy = new VacationPolicy(team, existing)

    const result = policy.canApprove({ from: '2026-07-05', to: '2026-07-10' })
    expect(result.allowed).toBe(false)
  })
})
```

**Route-Tests** — Hono hat einen eingebauten Test-Helper, kein Server-Start nötig:

```typescript
// api/tests/routes/vacations.test.ts
it('erstellt einen Urlaubsantrag', async () => {
  const res = await app.request('/api/vacations', {
    method: 'POST',
    body: JSON.stringify({ from: '2026-07-01', to: '2026-07-14' }),
    headers: { 'Content-Type': 'application/json' },
  })
  expect(res.status).toBe(201)
})
```

**Frontend-Tests** — Komponenten isoliert testen:

```typescript
// web/__tests__/planner-view.test.tsx
it('zeigt Urlaubseinträge an', () => {
  render(<PlannerView vacations={mockVacations} />)
  expect(screen.getByText('Urlaub: 01.07 – 14.07')).toBeInTheDocument()
})
```

---

## CLAUDE.md — Codequalität und Tests sicherstellen

Die CLAUDE.md ist die wichtigste Datei für Vibe-Coding-Qualität. Claude hält sich
an diese Regeln — ohne sie generiert Claude oft Code ohne Tests und mit
inkonsistentem Stil. Diese CLAUDE.md ins Repo-Root legen:

```markdown
# CLAUDE.md

## Projekt
Firmeninterner Jahresplaner. API-First Monorepo mit Hono (API), Next.js (Web), shared (Typen).

## Befehle
- `npm run dev` — startet API + Web parallel
- `npm test` — alle Tests (Vitest + React Testing Library)
- `npm run lint` — Linting
- `npm run build` — Production Build

## Tests
- Jede neue Domain-Klasse braucht Unit-Tests
- Jede neue Route braucht mindestens einen Happy-Path-Integrationstest
- Tests VOR der Implementierung schreiben wenn die Anforderung klar ist
- `npm test` muss vor jedem Commit grün sein
- Keine gemockten Implementierungsdetails — teste Verhalten, nicht Interna

## Code-Stil
- Funktionen und Variablen: sprechende Namen, keine Abkürzungen
  (`getActiveTeamMembers`, nicht `getATM`)
- Funktionen maximal 20 Zeilen — darüber hinaus aufteilen
- Maximal 2 Ebenen Einrückung pro Funktion (kein tief verschachteltes if/for/try)
- Early Return statt verschachtelter if-Blöcke
- Keine auskommentierten Code-Blöcke — löschen statt kommentieren
- Keine Magic Numbers — Konstanten mit sprechenden Namen

## Architektur
- Geschäftslogik gehört in `api/src/domain/`-Klassen, nicht in Routes
- Routes sind dünn: validieren, Domain aufrufen, Response zurückgeben
- Keine DB-Imports in `domain/`-Dateien
- Shared Types in `shared/` — keine Typ-Duplikate zwischen api und web

## TypeScript-Konventionen
- `strict: true` in tsconfig.json — immer
- Kein `any` — stattdessen `unknown` und Type Guards
- Kein `as` Type-Casting — stattdessen Type Guards oder Zod-Parsing
- `type` statt `interface` (konsistenter, kann Unions/Intersections)
- Keine TypeScript-Enums — stattdessen Union-Typen:
  `type Role = 'admin' | 'team-lead' | 'user'`
- Zod-Schema als Single Source of Truth — Typen daraus ableiten:
  `type Vacation = z.infer<typeof vacationSchema>`
- Explizite Return-Typen nur bei exportierten Funktionen, intern inferieren lassen
- Ergebnisse mit Discriminated Unions statt Exceptions:
  `{ ok: true, data: Vacation } | { ok: false, reason: string }`
- Typ-Imports explizit markieren: `import type { Vacation } from ...`
- Import-Sortierung: externe Packages → interne Packages → relative Imports

## Kommentare
- Nur kommentieren WARUM, nicht WAS
- Kein Kommentar ist besser als ein trivialer Kommentar
- JSDoc nur für öffentliche API-Funktionen in shared/

## MCP
Nutze immer context7 wenn du Code für Better-Auth, Hono oder Drizzle generierst.
```

---

## Hinweise für Vibe-Coding

### Was hervorragend funktioniert

- **Next.js, TypeScript, Tailwind** — Claude kennt diese Stacks sehr gut. Zuverlässigstes Vibe-Coding-Erlebnis.
- **Drizzle** — Schema-Definitionen und Queries sind vorhersagbar, Claude generiert zuverlässigen Code.
- **PostgreSQL / SQLite** — seit Jahrzehnten stabil, keinerlei Probleme.

### Worauf man achten muss

- **Better-Auth** — jung (2024), Claude's Trainingsdaten kennen die Library nur begrenzt. Claude wird möglicherweise veraltete API-Patterns vorschlagen oder auf Auth.js-Muster zurückfallen. **Immer gegen offizielle Doku prüfen.**
- **Hono** — besser als Better-Auth was Claude-Wissen angeht, aber bei neueren Features oder Edge Cases gegenprüfen.

### Empfohlene MCP-Erweiterungen

**Context7** (`@upstash/context7-mcp`) kompensiert das Wissenslücken-Problem bei neuen Libraries. Einrichtung:

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

Nutzung: `"use context7"` in die Nachricht schreiben — Claude holt dann gezielt
die aktuelle Doku der betroffenen Library (nicht alles, nur was relevant ist).

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
