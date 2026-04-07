# Schnappster — Weiterentwicklung zur Multi-User SaaS-Plattform

## Beschreibung

Schnappster ist aktuell eine Single-User-App ohne Authentifizierung. Die
Weiterentwicklung macht die App mehrbenutzerfähig: Nutzer können sich per
Google oder Facebook einloggen, sehen nur ihre eigenen Suchen und Schnäppchen,
und Administratoren verwalten die Plattform. Ziel ist ein bezahlter Dienst
im Internet.

---

## Geplanter Tech-Stack

### Geändert / Neu

| Komponente | Technologie | Beschreibung |
|---|---|---|
| **Datenbank** | PostgreSQL (via Supabase) | Ersetzt SQLite. Multi-User-fähig, concurrent writes, skalierbar |
| **Auth** | Supabase Auth | Google- und Facebook-OAuth eingebaut, User-Management-Dashboard, Passwort-Reset, E-Mail-Verifikation |
| **Datenisolierung** | PostgreSQL Row Level Security (RLS) | DB-seitige Zugriffskontrolle — jeder User sieht nur seine eigenen Daten, unabhängig vom Applikationscode |
| **Payments** | Stripe | Subscription-Management, Webhooks für Plan-Status, Industriestandard für SaaS |
| **Rollen** | Admin / User | Admin: voller Zugriff. User: nur eigene Daten. Erster User wird automatisch Admin |

### Unverändert

| Komponente | Technologie |
|---|---|
| **Backend** | FastAPI (Python) |
| **ORM** | SQLModel |
| **Scraping** | curl-cffi + BeautifulSoup |
| **AI-Analyse** | OpenAI-kompatible API (OpenRouter) |
| **Hintergrundjobs** | APScheduler |
| **Frontend** | Next.js + React + Tailwind + shadcn/ui |

---

## Begründungen und Vergleiche

### Warum Supabase?

| Kriterium | Supabase | Pure Postgres + Authlib | PocketBase | Keycloak |
|---|---|---|---|---|
| **Auth eingebaut** | ✅ komplett | ❌ selbst bauen (~300 Zeilen) | ✅ komplett | ✅ komplett |
| **Social Login** | ✅ Google, Facebook, etc. | ⚠️ Authlib (~100 Zeilen) | ✅ | ✅ |
| **User-Management-UI** | ✅ Dashboard | ❌ eigene Admin-Routen | ✅ | ✅ |
| **Passwort-Reset** | ✅ automatisch | ❌ selbst + E-Mail-Service | ✅ | ✅ |
| **RLS** | ✅ nativ integriert | ✅ manuell konfigurieren | ❌ nicht vorhanden | ❌ |
| **Datenbank** | PostgreSQL | PostgreSQL | SQLite (begrenzt) | eigene DB nötig |
| **Gewicht** | mittel (managed) | keins | leicht (1 Binary) | schwer (Java, viel RAM) |
| **Vendor-Lock-in** | mittel (self-host möglich) | keiner | niedrig | niedrig |
| **Skalierung** | ✅ PostgreSQL | ✅ PostgreSQL | ❌ SQLite-Locks | ✅ |

**Entscheidung Supabase** weil:
- Auth + DB + RLS aus einer Hand — minimaler Integrationsaufwand
- Managed Free Tier zum Start, Self-Hosting bei Bedarf möglich
- RLS als Sicherheitsnetz gegen Datenlecks (vergessene WHERE-Klauseln)
- User-Management-Dashboard spart eigene Admin-Routen
- PocketBase scheidet aus wegen SQLite (concurrent writes bei vielen Usern)
- Keycloak ist für eine App dieser Größe überdimensioniert

### Warum RLS?

**Pro:**
- Datenisolierung auf DB-Ebene — kein vergessenes `WHERE owner_id = ?` kann zu Datenlecks führen
- Funktioniert unabhängig vom Zugriffspfad (API, Admin-Tool, Reporting)
- Bei Supabase quasi kostenlos mitgeliefert

**Contra:**
- Komplexere Szenarien (Sharing, Org-Hierarchien) erfordern Join-Tabellen
- Debugging von Policies kann aufwendig sein
- Hintergrundprozesse (Scraper, Analyzer) laufen mit Service-Role und umgehen RLS — dort braucht es eigene Python-Logik

**Praktische Umsetzung:**
- API-Routen (User-Requests): nur RLS, kein WHERE nötig
- Hintergrundprozesse (Scraper): Service-Role + explizite Python-Logik
- Admin-Routen: Service-Role + `require_admin` Dependency

### Warum PostgreSQL statt SQLite?

SQLite ist single-writer — bei mehreren gleichzeitigen Usern die Suchen auslösen
kommt es zu Write-Locks. PostgreSQL ist für concurrent access gebaut.
Durch Supabase entsteht kein zusätzlicher Ops-Aufwand für den DB-Server.

### Warum Stripe?

Industriestandard für SaaS-Payments. Alternativen (Lemon Squeezy, Paddle) sind
einfacher bei EU-Steuerhandling, aber weniger flexibel. Stripe bietet Webhooks
die direkt mit FastAPI integrierbar sind.

---

## Hinweise für Vibe-Coding

### Was hervorragend funktioniert

- **FastAPI, SQLModel, Next.js, shadcn/ui** — Claude kennt diese Stacks sehr gut
- **RLS-Policies** — SQL-basiert, Claude generiert zuverlässige Policies
- **Stripe-Grundmuster** — Webhooks, Subscriptions, Customer-Objekte kennt Claude gut
- **pytest + FastAPI TestClient** — bewährtes Pattern, Claude folgt es zuverlässig

### Worauf man achten muss

- **`supabase-py`** — der Python-Client ist weniger verbreitet als der JS-Client. Bei neueren Features gegen offizielle Doku prüfen. **Context7 nutzen.**
- **RLS + Service-Role-Trennung** — immer explizit kommunizieren ob ein Code-Block im User-Context (RLS aktiv) oder Service-Context (RLS bypassed) laufen soll. Sonst generiert Claude entweder unnötige WHERE-Klauseln oder lässt nötige Checks weg.
- **Stripe API-Versionen** — Stripe ändert regelmäßig die API. Aktuelle Stripe-Doku beim Implementieren von Webhooks als Kontext mitgeben. **Context7 nutzen.**
- **APScheduler + Multi-Tenancy** — Background-Jobs kennen keinen User-Context. Claude generiert hier leicht Code der RLS voraussetzt aber nicht bekommt. Explizit darauf hinweisen dass Jobs mit Service-Role laufen und `owner_id` explizit setzen müssen.

### Context7 MCP-Server einrichten

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

Die bestehende CLAUDE.md um folgende Abschnitte erweitern:

<details>
<summary>Ergänzungen für die CLAUDE.md anzeigen</summary>

```markdown
## Multi-Tenancy

- Alle User-Daten tragen `owner_id` (UUID aus Supabase Auth)
- API-Routen laufen im User-Context — RLS filtert automatisch, kein WHERE nötig
- Hintergrundprozesse (Scraper, Analyzer) laufen mit Service-Role — RLS ist bypassed,
  `owner_id` muss explizit in alle Queries und Inserts gesetzt werden
- Admin-Routen: Service-Role + `require_admin` Dependency

## Zwei DB-Verbindungen

- `get_db_session()` — User-Context, RLS aktiv (für API-Routen)
- `get_admin_session()` — Service-Role, RLS bypassed (für Background-Jobs, Admin)
- Niemals Service-Role-Key im Frontend oder in API-Routen die User-Input verarbeiten

## Tests

- Supabase Auth in Tests mocken: JWT mit Test-User-ID faken, nicht echte Supabase-Instanz
- RLS-Policies separat in Supabase testen (außerhalb von pytest)
- Fixtures für User-Context und Service-Context getrennt halten
- `uv run pytest` muss vor jedem Commit grün sein

## Bestehende Konventionen (nicht ändern)

- Schema-Änderungen: `uv run dbreset` (kein Alembic)
- DB-Pfad immer über `get_app_root()` — nie relative Pfade
- SQLModel-Muster: Tabellen-Definition + Read/Create/Update-Schemas in derselben Datei
- Background-Jobs: ScraperService und AIService haben je eine Single-Worker-Queue —
  Jobs dürfen sich nicht überlappen
- `AppSettings`-Tabelle für runtime-konfigurierbare Einstellungen
- API-Keys (`OPENAI_API_KEY`, `SUPABASE_URL`, `STRIPE_SECRET_KEY` etc.) nur in `.env`

## MCP
Nutze immer context7 wenn du Code für supabase-py oder Stripe generierst.
```

</details>

---

## Umsetzungsreihenfolge

1. **Phase 1 — Auth & Multi-Tenancy:** SQLite → PostgreSQL, `owner_id` auf AdSearch + Ad, Supabase OAuth (Google + Facebook), RLS-Policies, Admin-Rolle, zwei DB-Sessions (`get_db_session` / `get_admin_session`)
2. **Phase 2 — Payments:** Stripe-Subscriptions, Webhooks → User-Plan in DB, Feature-Gates (max. Suchen pro Plan)
3. **Phase 3 — Betrieb:** Rate-Limiting, Monitoring (Sentry), Transactional E-Mails
