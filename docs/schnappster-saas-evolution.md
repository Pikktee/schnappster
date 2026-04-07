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

### Was gut funktioniert

- **FastAPI, SQLModel, Next.js, shadcn/ui** — Claude kennt diese Stacks hervorragend. Sehr zuverlässiges Vibe-Coding.
- **Supabase-Integration** — gut dokumentiert, Claude hat solide Trainingsdaten dafür.
- **RLS-Policies** — SQL-basiert, Claude generiert zuverlässige Policies.

### Worauf man achten sollte

- **Supabase Python-Client (`supabase-py`)** — weniger verbreitet als der JS-Client. Claude kennt die API, aber bei neueren Features gegenprüfen.
- **RLS + Service-Role-Trennung** — klar kommunizieren ob ein Code-Block im User-Context (RLS aktiv) oder Service-Context (RLS umgangen) läuft. Sonst generiert Claude möglicherweise unnötige WHERE-Klauseln oder lässt nötige Checks weg.
- **Stripe-Webhooks** — Claude kennt die Grundmuster gut, aber Stripe ändert regelmäßig API-Versionen. Aktuelle Stripe-Doku als Kontext mitgeben.

### Empfohlene MCP-Erweiterungen

- **Context7** (`@upstash/context7-mcp`) — aktuelle Bibliotheks-Dokumentation bei Bedarf in den Kontext laden. Besonders nützlich für Supabase-spezifische Fragen.

### Umsetzungsreihenfolge

1. **Phase 1 — Auth & Multi-Tenancy:** SQLite → PostgreSQL, User-Modell, Supabase OAuth, RLS-Policies, Admin-Rolle
2. **Phase 2 — Payments:** Stripe-Subscriptions, Webhooks, Feature-Gates (max. Suchen pro Plan)
3. **Phase 3 — Betrieb:** Rate-Limiting, Monitoring (Sentry), Transactional E-Mails
