# Jahresplaner — Tech-Stack und Architekturentscheidungen

## Beschreibung

Ein firmeninternes Web-Tool zur Jahresplanung, genutzt von allen Teams und
Abteilungen eines mittelständischen Unternehmens. API-First-Architektur:
das Frontend ist austauschbar (Web jetzt, Mobile App perspektivisch).
Komplett self-hosted, keine externen Managed-Services.

---

## Geplanter Tech-Stack

### Backend

| Komponente | Technologie | Beschreibung |
|---|---|---|
| **Sprache** | TypeScript | Shared Types zwischen API und Frontend — kein manuelles Synchronisieren von Datenmodellen |
| **API-Framework** | [Hono](https://hono.dev) | Ultraleichtes (~14kb) API-Framework. Läuft auf Node.js, Bun oder Deno. Typsicher, schnell, minimalistisch |
| **Auth** | [Better-Auth](https://better-auth.com) | Self-hosted Auth-Library. E-Mail+Passwort, später SSO (Microsoft/Google) ohne Architekturumbau. YC-backed, $5M Funding |
| **ORM** | [Drizzle](https://orm.drizzle.team) | Typsicheres ORM. Unterstützt SQLite und PostgreSQL mit identischer API — DB-Wechsel ist ein Import-Austausch |
| **Datenbank** | SQLite → PostgreSQL | SQLite zum Start (einfach, keine Server-Infrastruktur), PostgreSQL bei wachsender Last |
| **E-Mail** | Firmen-SMTP | Passwort-Reset und Benachrichtigungen über bestehende Firmen-Mailinfrastruktur |

### Frontend

| Komponente | Technologie | Beschreibung |
|---|---|---|
| **Framework** | [Next.js](https://nextjs.org) | Reiner UI-Layer, keine eigene API-Logik. Austauschbar ohne API-Änderungen |
| **API-Anbindung** | fetch / SWR | Kommunikation gegen Hono-API via `NEXT_PUBLIC_API_URL` |

### Deployment

```yaml
# docker-compose.yml
services:
  api:      # Hono + Better-Auth (Node.js oder Bun)
  web:      # Next.js
  # postgres: # optional, wenn SQLite nicht mehr ausreicht
```

Alles self-hosted, läuft auf jedem Linux-Server oder intern im Firmennetz.

---

## Auth — Migrationspfad

```
Phase 1 (jetzt):   E-Mail + Passwort (Better-Auth)
                    Passwort-Reset via Firmen-SMTP
                    Rollen: Admin, Team-Lead, Mitarbeiter

Phase 2 (später):  + Microsoft 365 / Azure AD SSO   (ein Config-Block in Better-Auth)
                   + Google Workspace SSO            (ein Config-Block in Better-Auth)
                   Bestehende Accounts bleiben, werden automatisch verknüpft
```

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

---

## Repo-Struktur: Monorepo

Frontend, Backend und perspektivisch Mobile App leben in einem Repository:

```
jahresplaner/
  packages/
    api/            ← Hono + Better-Auth + Drizzle
      src/
        routes/     ← HTTP-Handler (dünn)
        domain/     ← Geschäftslogik-Klassen
        db/         ← Drizzle-Schema, Migrations
        middleware/  ← Auth, Error-Handling
        lib/        ← Hilfsfunktionen, SMTP
      tests/
    web/            ← Next.js (reiner UI-Layer)
      app/          ← App Router, Seiten + Layouts
      components/   ← UI-Primitives + Feature-Komponenten
      lib/          ← API-Client, Auth-Client
      hooks/        ← useVacations(), useTeam(), etc.
    shared/         ← API-Vertrag (nur Typen + Zod-Schemas)
      types/
      schemas/
    mobile/         ← React Native (perspektivisch)
  package.json      ← Workspace-Root
  docker-compose.yml
```

**Warum Monorepo?**
- Shared Types zwischen API und Frontend — der Hauptvorteil von TypeScript geht
  verloren wenn die Typen in getrennten Repos liegen
- Vibe-Coding: Claude muss API und Frontend gleichzeitig sehen um konsistente
  Änderungen zu machen. Bei getrennten Repos fehlt der Kontext
- Eine Änderung, ein Commit — API-Endpoint + Frontend-Call + Typen gehören zusammen
- Kein Versions-Chaos zwischen Frontend und API

Separate Repos lohnen sich erst wenn getrennte Teams unabhängig deployen müssen.

---

## Deployment

Zwei separate Prozesse hinter einem Reverse Proxy (Caddy), eine Domain:

```
https://jahresplaner.firma.de      →  Next.js (:3000)
https://jahresplaner.firma.de/api  →  Hono    (:4000)
```

```yaml
# docker-compose.yml
services:
  api:
    build: ./packages/api
    ports: ["4000:4000"]
    environment:
      - DATABASE_URL=file:./data/db.sqlite
      - BETTER_AUTH_SECRET=...
      - SMTP_HOST=mail.firma.de
  web:
    build: ./packages/web
    ports: ["3000:3000"]
    environment:
      - NEXT_PUBLIC_API_URL=https://jahresplaner.firma.de/api
  caddy:
    image: caddy:2
    ports: ["443:443"]
```

`docker compose up` — drei Container, ein Befehl. API und Frontend unabhängig
deploybar, skalierbar, und bei Fehlern voneinander isoliert.

---

## Geschäftslogik isolieren

Geschäftsregeln gehören weder in Routes noch in DB-Queries — sie werden in eigenen
Klassen gekapselt. Reine Funktionen/Klassen ohne DB- oder HTTP-Abhängigkeit,
testbar mit simplen Objekten.

**Faustregel:** Eine einzelne Regel → eigene Funktion. Mehrere zusammengehörige
Regeln auf denselben Daten → eigene Klasse.

```typescript
// domain/vacation-policy.ts — kennt keine DB, kein HTTP
export class VacationPolicy {
  constructor(
    private team: Team,
    private existingVacations: Vacation[]
  ) {}

  canApprove(request: VacationRequest): Result {
    if (this.exceedsTeamCapacity(request)) {
      return { allowed: false, reason: 'Zu viele gleichzeitig abwesend' }
    }
    if (this.exceedsIndividualBudget(request)) {
      return { allowed: false, reason: 'Urlaubskontingent erschöpft' }
    }
    if (this.conflictsWithFreeze(request)) {
      return { allowed: false, reason: 'Urlaubssperre in diesem Zeitraum' }
    }
    return { allowed: true }
  }

  private exceedsTeamCapacity(request: VacationRequest): boolean {
    const concurrent = this.existingVacations.filter(v => overlaps(v, request))
    return concurrent.length / this.team.members.length > 0.3
  }

  private exceedsIndividualBudget(request: VacationRequest): boolean { ... }
  private conflictsWithFreeze(request: VacationRequest): boolean { ... }
}
```

```typescript
// Route — dünn, nur Verdrahtung
app.post('/api/vacations', async (c) => {
  const data = await c.req.json()
  const team = await teamRepo.getWithMembers(data.teamId)
  const existing = await vacationRepo.getForPeriod(data.teamId, data.from, data.to)

  const policy = new VacationPolicy(team, existing)
  const result = policy.canApprove(data)
  if (!result.allowed) return c.json({ error: result.reason }, 400)

  await vacationRepo.create(data)
  return c.json({ ok: true })
})
```

Kein volles DDD/Hexagonal-Framework nötig — nur diese saubere Trennung. Wächst die
Komplexität, kann daraus schrittweise eine formale Domänenschicht werden.

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

Alternativ in `CLAUDE.md` festlegen:
```markdown
Nutze immer context7 wenn du Code für Better-Auth, Hono oder Drizzle generierst.
```

### Umsetzungsreihenfolge

1. **API-Grundgerüst:** Hono-Server + Drizzle + SQLite aufsetzen
2. **Auth:** Better-Auth integrieren (E-Mail+Passwort)
3. **Frontend:** Next.js als UI-Layer gegen Hono-API anbinden
4. **Rollen:** Admin / Team-Lead / Mitarbeiter implementieren
5. **Features:** Planungsfunktionen, Team-Zuordnungen, Kalender-Views
6. **Deployment:** Docker Compose für internen Server
