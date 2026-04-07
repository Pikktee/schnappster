# Schnappster — Weiterentwicklung zur Multi-User SaaS-Plattform

## Beschreibung

Schnappster ist aktuell eine Single-User-App ohne Authentifizierung. Die
Weiterentwicklung macht die App mehrbenutzerfähig: Nutzer können sich per
Google oder Facebook einloggen und sehen nur ihre eigenen Suchen und Schnäppchen.
Admins haben dieselbe Datenisolierung, zusätzlich aber Zugriff auf Logs,
App-Settings und Betriebsfunktionen. Perspektivisch soll die App als
bezahlter Dienst angeboten werden (Payments vorerst nicht im Scope).

---

## Geplanter Tech-Stack

### Geändert / Neu

| Komponente | Technologie | Beschreibung |
|---|---|---|
| **Datenbank** | PostgreSQL (via Supabase) | Ersetzt SQLite. Multi-User-fähig, concurrent writes, skalierbar |
| **Auth** | Supabase Auth | Google- und Facebook-OAuth eingebaut, User-Management-Dashboard, Passwort-Reset, E-Mail-Verifikation |
| **Datenisolierung** | PostgreSQL Row Level Security (RLS) | DB-seitige Zugriffskontrolle — jeder User sieht nur seine eigenen Daten, gilt für User und Admin gleichermaßen |
| **Rollen** | Admin / User | Gleiche Datenisolierung für beide. Admins haben zusätzlich Zugriff auf Logs, App-Settings, Statistiken und Admin-Funktionen. User-Verwaltung läuft über Supabase-Dashboard |

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

---

## Hinweise für Vibe-Coding

### Was hervorragend funktioniert

- **FastAPI, SQLModel, Next.js, shadcn/ui** — Claude kennt diese Stacks sehr gut
- **RLS-Policies** — SQL-basiert, Claude generiert zuverlässige Policies
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

### Umgebungen

- **Unit-Tests (pytest):** Supabase-Auth mocken (`app.dependency_overrides[get_current_user]`),
  In-Memory-PostgreSQL oder lokales PostgreSQL — schnell, kein Netzwerk, CI-fähig
- **Integrationstests:** Supabase lokal via Docker (`npx supabase start`) —
  RLS-Policies und volle Supabase-Features testbar
- **Staging:** Eigenes Supabase-Projekt (`schnappster-dev`) — isoliert von Produktion
- **Produktion:** `schnappster-prod` — wird nie für Tests verwendet

### Regeln

- Supabase-Auth in Unit-Tests immer mocken — nie gegen Remote-DB testen
- RLS-Policies in der lokalen Supabase-Instanz testen, nicht in pytest
- Fixtures für User-Context und Admin-Context getrennt halten
- `uv run pytest` muss vor jedem Commit grün sein
- Teste Verhalten, nicht Implementierungsdetails — kein Mocken interner Methoden
- Neue Services und Filterfunktionen brauchen Unit-Tests (wie bestehende `test_scraper_filters.py`)

## Code-Stil

- Funktionen und Variablen: sprechende Namen, keine Abkürzungen (`get_active_searches`, nicht `get_as`)
- Funktionen maximal ~20 Zeilen — größere Logik in Hilfsmethoden auslagern
- Early Return statt verschachtelter if-Blöcke
- Keine auskommentierten Code-Blöcke — löschen statt auskommentieren
- Keine Magic Numbers — Konstanten mit sprechenden Namen (`MAX_ADS_PER_RUN = 10`)
- Kommentare nur WARUM, nicht WAS

## Python & FastAPI Konventionen

- Vollständige Type Hints überall — Pyright ist konfiguriert, kein `Any` ohne Begründung
- Kein `# type: ignore` außer wo absolut unvermeidbar
- Routes sind dünn: Request validieren → Service aufrufen → Response zurückgeben
- Services via `Depends()` injizieren, nicht in Routes instanziieren
- HTTP-Statuscodes explizit setzen (`status_code=201`, `status_code=204`)
- Pydantic/SQLModel-Schemas für alle Request- und Response-Typen — kein `dict`
- Exceptions als `HTTPException` mit sprechendem `detail`-Text
- Async wo sinnvoll — IO-bound Operationen (HTTP, DB) async, CPU-bound sync

## Bestehende Konventionen (nicht ändern)

- Schema-Änderungen: `uv run dbreset` (kein Alembic)
- DB-Pfad immer über `get_app_root()` — nie relative Pfade
- SQLModel-Muster: Tabellen-Definition + Read/Create/Update-Schemas in derselben Datei
- Background-Jobs: ScraperService und AIService haben je eine Single-Worker-Queue —
  Jobs dürfen sich nicht überlappen
- `AppSettings`-Tabelle für globale runtime-konfigurierbare Einstellungen (Admin)
- `UserSettings`-Tabelle für benutzerspezifische Einstellungen (Telegram Chat-ID, Benachrichtigungen)
- Telegram Bot-Token in `.env` — Chat-ID je User in `UserSettings`
- Avatar kommt als URL aus der Supabase Auth Session (OAuth-Provider) — kein eigenes Storage
- API-Keys (`OPENAI_API_KEY`, `SUPABASE_URL` etc.) nur in `.env`

## MCP
Nutze immer context7 wenn du Code für supabase-py generierst.
```

</details>

---

## Benutzerprofil & Benachrichtigungen

### Benutzerprofil

Jeder User hat ein Profil mit:

| Feld | Quelle | Beschreibung |
|---|---|---|
| **Name** | OAuth-Provider (editierbar) | Anzeigename, initial aus Google/Facebook übernommen |
| **Avatar** | OAuth-Provider (automatisch) | Profilbild von Google/Facebook — kein Upload |
| **E-Mail** | Supabase Auth (read-only) | Aus der Auth-Session, nicht änderbar |

Der Avatar wird direkt vom OAuth-Provider bezogen (URL aus der Supabase Auth Session) — kein Upload, kein Speichern im eigenen Storage.

### Benachrichtigungen

Benachrichtigungskanäle pro Benutzer:

| Kanal | Beschreibung |
|---|---|
| **Telegram** | Geteilter Bot-Token in `.env` (Admin konfiguriert den Bot), User trägt seine eigene Chat-ID ein |
| **Web Push** | Browser-Push-Benachrichtigungen |
| **E-Mail** | An die aus Supabase Auth bekannte E-Mail-Adresse |

Benachrichtigungseinstellungen:
- **Kanal-Auswahl:** Telegram / Web Push / E-Mail (mehrere kombinierbar)
- **Mindest-Score:** Schwellwert 0–10 — nur Schnäppchen ab diesem `bargain_score` werden gemeldet
- **Modus:** `instant` (sofort bei neuem Fund) oder `daily_summary` (einmal täglich zusammengefasst)

### UserSettings-Tabelle

```python
class UserSettings(SQLModel, table=True):
    user_id: uuid.UUID          # FK → Supabase auth.uid, Primary Key
    display_name: str | None    # Anzeigename (initial aus OAuth übernommen)
    telegram_chat_id: str | None
    notify_telegram: bool = False
    notify_email: bool = False
    notify_web_push: bool = False
    notify_min_score: int = 5   # 0–10
    notify_mode: str = "instant"  # "instant" | "daily_summary"
```

### Trennung: UserSettings vs. AppSettings

| Einstellung | Wo | Wer |
|---|---|---|
| Telegram Bot-Token | `.env` | Admin (globale Konfiguration) |
| Telegram Chat-ID | `UserSettings` | User (persönliche Einstellung) |
| Globale Filter-Regeln, Scraper-Einstellungen | `AppSettings` | Admin |
| Benachrichtigungskanal, Mindest-Score, Modus | `UserSettings` | User |

---

## Umsetzungsreihenfolge

1. **Phase 1 — Auth & Multi-Tenancy:** SQLite → PostgreSQL, `owner_id` auf AdSearch + Ad, Supabase OAuth (Google + Facebook), RLS-Policies, Admin-Rolle, zwei DB-Sessions (`get_db_session` / `get_admin_session`), `UserSettings`-Tabelle (Profil + Benachrichtigungseinstellungen)
2. **Phase 2 — Admin-Bereich:** Log-Bereich absichern (`require_admin`), App-Settings-Route absichern, Manuell Scrape/Analyze auslösen, System-Statistiken
3. **Phase 3 — Betrieb:** Benachrichtigungen (Telegram, Web Push, E-Mail), Rate-Limiting, Monitoring (Sentry)
4. **Phase 4 — Payments (perspektivisch):** Stripe-Subscriptions, Webhooks, Feature-Gates
