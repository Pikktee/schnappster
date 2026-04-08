# Schnappster — Weiterentwicklung zur Multi-User SaaS-Plattform

> **Nur Planung:** Diese Datei beschreibt **geplante** Features und Migrationsschritte. Sie ist **kein** dauerhaftes Projekt-Handbuch. Stabile Konventionen in **`AGENTS.md`** pflegen; **`CLAUDE.md`** ist ein Symlink darauf. Von Agenten-Dateien **nicht** auf dieses Dokument verweisen.

## Beschreibung

Schnappster ist aktuell eine Single-User-App ohne Authentifizierung. Die
Weiterentwicklung macht die App mehrbenutzerfähig: Nutzer können sich per
Google oder Facebook einloggen und sehen nur ihre eigenen Suchen und Schnäppchen.
Für **ihre eigenen** Daten gelten für Admins dieselben Mandantenregeln wie für
normale User; **zusätzlich** erhalten Admins über RLS/Policies und geschützte
Routen Zugriff auf Logs, globale App-Settings und Betriebsfunktionen.
Perspektivisch soll die App als
bezahlter Dienst angeboten werden (Payments vorerst nicht im Scope).

---

## Geplanter Tech-Stack

### Geändert / Neu

| Komponente | Technologie | Beschreibung |
|---|---|---|
| **Datenbank** | PostgreSQL (via Supabase) | Ersetzt SQLite. Multi-User-fähig, concurrent writes, skalierbar |
| **Auth** | Supabase Auth | Google- und Facebook-OAuth eingebaut, User-Management-Dashboard, Passwort-Reset, E-Mail-Verifikation |
| **Datenisolierung** | PostgreSQL Row Level Security (RLS) | Reguläre User nur eigene Mandantendaten (`owner_id` / `user_id`). Admins gleiches Prinzip für **eigene** Daten **plus** zusätzliche Policies für Admin-Ressourcen (z. B. `app_settings`, ggf. Querschnitt für Statistiken) |
| **Rollen** | Admin / User | User: nur eigene Suchen/Anzeigen/Einstellungen. Admin: oben genannte Zusatzrechte (Logs, globale Settings, Stats, manuelle Jobs). User-Verwaltung über Supabase-Dashboard |

Hinweis für spätere Payments: Zusätzliche bezahlte Stufen möglichst **nicht** als neue Admin-Rollen modellieren, sondern separat als Plan/Entitlements (z. B. `free`, `premium`) neben `role` (`user`/`admin`), damit Rechteverwaltung und Monetarisierung sauber getrennt bleiben.

### Unverändert

| Komponente | Technologie |
|---|---|
| **Backend** | FastAPI (Python) |
| **ORM** | SQLModel |
| **Scraping** | curl-cffi + BeautifulSoup |
| **AI-Analyse** | OpenAI-kompatible API (OpenRouter) |
| **Hintergrundjobs** | APScheduler |
| **Frontend** | Next.js + React + Tailwind + shadcn/ui |

### Verbindliche Festlegung: Admin-HTTP = Variante B

- **Jede FastAPI-Route, die einen HTTP-Request bearbeitet** (normale User **und** Admins), nutzt **`get_db_session()`** mit gesetztem **User-JWT** — **RLS bleibt immer aktiv**. Admin-Rechte: `Depends(require_admin)` **plus** passende **RLS-Policies** (JWT `app_metadata.role = 'admin'`), z. B. für `app_settings` und bei Bedarf weitere Tabellen (Logs, Statistiken).
- **`get_admin_session()` (Service-Role, RLS umgangen)** ist **ausschließlich** für **Hintergrundjobs** (Scraper, Analyzer) — **niemals** für Admin-Dashboard-, Settings- oder Stats-HTTP-Endpunkte.
- **`DELETE /users/me`:** Kaskade auf App-Tabellen mit **`get_db_session()`** (nur eigene Zeilen; RLS muss `DELETE` für den Besitzer erlauben). Anschließend Löschen des **Supabase-Auth-Users** über die **Supabase Admin API** (Service-Role-**Key**, typisch `auth.admin.delete_user` o. ä.) — das ist **kein** „Admin-Dashboard mit God-DB-Session“, sondern ein klar abgegrenzter Auth-Vorgang innerhalb dieser einen Route.

**Variante A** (Service-Role-**SQL-Session** für Admin-HTTP) ist **nicht** vorgesehen.

---

## Hinweise für Vibe-Coding

### Was hervorragend funktioniert

- **FastAPI, SQLModel, Next.js, shadcn/ui** — Claude kennt diese Stacks sehr gut
- **RLS-Policies** — SQL-basiert, Claude generiert zuverlässige Policies
- **pytest + FastAPI TestClient** — bewährtes Pattern, Claude folgt es zuverlässig

### Worauf man achten muss

- **`supabase-py`** — der Python-Client ist weniger verbreitet als der JS-Client. Bei neueren Features gegen offizielle Doku prüfen. **Context7 nutzen.**
- **RLS + Service-Role-Trennung** — immer explizit kommunizieren ob ein Code-Block im User-Context (RLS aktiv) oder Service-Context (RLS bypassed) laufen soll. Sonst generiert Claude entweder unnötige WHERE-Klauseln oder lässt nötige Checks weg.
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

### Konventionen für die Umsetzungsphase (Code-Qualität, Tests, Architektur)

> Die folgenden Punkte waren früher als „CLAUDE.md-Ergänzung“ gedacht — sie bleiben **hier** als **Planungs- und Arbeitsreferenz** für die Migration. Was sich bewährt, später gezielt in **`AGENTS.md`** übernehmen (ohne diese Planungsdatei dauerhaft zu verlinken).

#### Multi-Tenancy

- Alle User-Daten tragen `owner_id` (UUID aus Supabase Auth).
- **Alle HTTP-Routen** (User und Admin): `get_db_session()` — RLS aktiv; Mandanten-Daten ohne manuelles `WHERE owner_id`; Admin-Zusatzrechte nur über RLS-Policies (`role = admin`).
- Hintergrundprozesse (Scraper, Analyzer) laufen mit Service-Role — RLS ist bypassed, `owner_id` muss explizit in alle Queries und Inserts gesetzt werden.
- Admin-HTTP: **Variante B** — nur `get_db_session()` + `require_admin` + RLS-Admin-Policies (siehe **Verbindliche Festlegung** oben).
- `get_admin_session()`: **nur** Background-Jobs, **nie** für Admin-HTTP-Handler. `DELETE /users/me`: App-Daten mit User-Session, Auth-User per Supabase Admin API (Service-Key), nicht `get_admin_session`.

#### Zwei DB-Verbindungen

- `get_db_session()` — User-Context, RLS aktiv (**alle HTTP-Routen**, inkl. Admin).
- `get_admin_session()` — Service-Role, RLS bypassed (**nur** APScheduler/Background-Jobs).
- Niemals Service-Role-Key ins Frontend; Service-Role nur in Server-Code mit klar abgegrenzten Pfaden.

#### Tests

**Was wird „gemockt“?**

- **Supabase Auth** (`get_current_user`, JWT): in den meisten **pytest**-Läufen **mocken** (z. B. `dependency_overrides`), damit kein Netz und kein Supabase-Auth-Aufruf nötig ist.
- **Die Datenbank:** typischerweise **nicht** durch einen generischen Supabase-Mock ersetzen — **echte PostgreSQL-Instanz** (lokal, Docker, CI), damit SQLModel/Constraints stimmen.
- **Kurz:** Auth mocken, **DB real (Postgres)** — zwei verschiedene Dinge.

**Muss lokal Postgres laufen? Reicht SQLite?**

- Nach Umstellung auf Postgres/`asyncpg`: jeder Test mit echtem SQL gegen die App-DB braucht **irgendwo PostgreSQL** (lokal oder nur CI).
- **SQLite** ersetzt das für die Haupt-Suite **nicht** (Treiber, Dialekt, kein RLS).
- Ohne laufende DB: nur Tests **ohne** DB (reine Logik) oder mit komplett gemockter Session.

**Umgebungen**

- **pytest:** Auth mocken; Postgres lokal/CI; kein Prod.
- **RLS-Integration (optional):** `npx supabase start` oder isoliertes Projekt — keine parallelen CI-Läufe gegen eine geteilte Dev-DB ohne Isolation.
- **Produktion:** nie für automatisierte Tests.

**Regeln**

- Supabase-Auth in pytest mocken — nicht gegen Remote-Prod testen.
- RLS in einer **Supabase-** oder Postgres-Umgebung testen, nicht durch „alles mocken“.
- Fixtures für User-Context und Admin-Context getrennt.
- `uv run pytest` vor Commit grün; Verhalten testen, keine internen Implementierungsdetails mocken.
- Neue Services/Filter: Unit-Tests wie bei bestehenden Tests (z. B. `test_scraper_filters.py`).

#### Code-Stil

- Sprechende Namen, keine unnötigen Abkürzungen (`get_active_searches`, nicht `get_as`).
- Funktionen möglichst **~20 Zeilen** — größere Logik in Hilfsmethoden.
- **Early return** statt tiefer Verschachtelung.
- Keine auskommentierten Codeblöcke — löschen statt auskommentieren.
- Keine Magic Numbers — benannte Konstanten (`MAX_ADS_PER_RUN = 10`).
- Kommentare nur **WARUM**, nicht **WAS**.

#### Python & FastAPI

- Vollständige Type Hints — Pyright ist konfiguriert, kein `Any` ohne Begründung.
- Kein `# type: ignore` außer wo unvermeidbar.
- Routes **dünn:** validieren → Service → Response.
- Services per `Depends()` injizieren, nicht in Routes instanziieren.
- HTTP-Statuscodes explizit (`201`, `204`, …).
- Pydantic/SQLModel-Schemas für Requests/Responses — kein loses `dict`.
- `HTTPException` mit klarem `detail`.
- **Async** wo sinnvoll (IO-bound async, CPU-bound sync).

#### Weitere Konventionen (SaaS-Zielzustand)

- Schema: Supabase CLI (`supabase migration new`), SQL unter `supabase/migrations/` — im Zielzustand kein `uv run dbreset` für Schemawechsel mehr.
- SQLModel: Tabellen + Read/Create/Update in **derselben** Datei.
- Background-Jobs: Scraper und Analyzer je **Single-Worker-Queue**, keine Überlappung.
- `AppSettings`: nur Admins — RLS mit Policy nur für `app_metadata.role = 'admin'`.
- `UserSettings`: pro User (Telegram Chat-ID, Benachrichtigungen).
- Konto-Löschung: App-Daten mit User-Session/RLS; Auth-User per Admin API; Haupt-Admin schützen (`403`).
- Telegram Bot-Token in `.env`; Chat-ID in `UserSettings`.
- Avatar aus OAuth/Supabase Session — kein eigenes Storage.
- Passwort ändern über Supabase Auth API.
- API-Keys nur in `.env`.
- Öffentliche Pflichtseiten: `/impressum`, `/datenschutz` — Middleware-Ausnahmen.
- CORS: bei abweichenden Origins `CORSMiddleware` + `CORS_ORIGINS` (kein `*` mit Credentials).
- Admin-Rolle nur in **`app_metadata`**; `require_admin` und RLS aus derselben Quelle — supabase-py-Feldnamen per Context7/Doku prüfen.

#### MCP

- Bei Code für **supabase-py** möglichst **Context7** (oder aktuelle offizielle Doku) nutzen.

### Agent-Dateien nach der Umsetzung

Diese Datei ist **kein** Ziel für dauerhafte Verweise aus `AGENTS.md` / `CLAUDE.md` oder Cursor-Rules.

**Nach** (oder während) der Implementierung: **`AGENTS.md`** an den **Ist-Zustand** anpassen — u. a. neue Sektion **„SaaS / multi-tenancy“** (Regeln aus diesem Dokument und Abschnitt **Konventionen für die Umsetzungsphase**), Befehle (`dbreset` vs. Migrationen), DB-Pfade, Test-Hinweise (Postgres, Auth-Mocks). Bis dahin bleibt `AGENTS.md` **ohne** geplante Features. Diese Planungsdatei kann danach **archiviert, gekürzt oder gelöscht** werden.

| Datei | Rolle |
|--------|--------|
| **`AGENTS.md`** | **Kanonische** Agenten-Anleitung (Cursor, Codex, …) — **hier editieren** |
| **`CLAUDE.md`** | Symlink → `AGENTS.md` (Claude Code erwartet den Dateinamen) |
| **`docs/schnappster-saas-evolution.md`** | **Nur** Planung — nicht verlinken |

<details>
<summary><strong>AGENTS.md-Ergänzungen nach der Migration</strong> (zum Aufklappen & Kopieren)</summary>

Nach **Postgres + Supabase + Multi-Tenancy** die folgenden Teile in **`AGENTS.md`** übernehmen (Sprache Englisch wie die restliche Datei). **`Key conventions`** und **`Testing`** anpassen; neue Sektion vor **`## Output Format`** einfügen. **Commands** (Static Export vs. Next-Node, `npm run build`, Docker) an den dann gültigen Stack anpassen — siehe Deployment-Abschnitt in diesem Dokument. Ergänzend gelten die inhaltlichen Regeln unter **Konventionen für die Umsetzungsphase** weiter oben in diesem Dokument (teilweise Deutsch, fürs Vibe-Coding).

**1. In `### Key conventions` — die Bullet „Database“ und „AppSettings“ ersetzen durch:**

```markdown
- **Database:** PostgreSQL (Supabase). No Alembic — schema changes via **Supabase migrations** (`supabase/migrations/`); do not use `uv run dbreset` as the primary workflow for schema evolution. Paths and connection string via app settings / env. **RLS** is enforced — see **SaaS / multi-tenancy** below.
- API keys (`OPENAI_API_KEY`, `OPENAI_MODEL`, `OPENAI_BASE_URL`) live in `.env`, not the DB
- **`AppSettings`:** global runtime settings (seller filters, Telegram, etc.). **Admin-only** in the DB (RLS policies) — see **SaaS / multi-tenancy**.
```

*(Die übrigen Key-conventions-Bullets davor/danach unverändert lassen, außer ihr ändert bewusst noch Felder wie `SUPABASE_*` in `.env`.)*

**2. In `## Testing` — nach den bestehenden Bullets ergänzen:**

```markdown
- With **Supabase auth**: mock **`get_current_user`** / auth in most tests; use a **real PostgreSQL** for tests that execute SQL against the app schema (SQLite is not a substitute for the main suite when production is Postgres). For **supabase-py**, verify APIs against current docs or **Context7**.
```

**3. Neue Sektion vor `## Output Format` einfügen:**

```markdown
## SaaS / multi-tenancy

Multi-tenant Postgres + Supabase Auth + RLS. Single-user SQLite no longer applies.

**Rules of thumb:**

- Tenant data uses **`owner_id`** (Supabase Auth user id). **All HTTP routes** (users and admins) use **`get_db_session()`** with JWT so **RLS stays on**. No manual `WHERE owner_id = …` for normal tenant queries.
- **`get_admin_session()`** (service role, RLS bypass) **only** for **APScheduler / background jobs** — never as the default for admin HTTP routes (admin UI uses user JWT + RLS).
- **Admin HTTP:** `require_admin` + **RLS policies** for `app_metadata.role = admin` (e.g. `app_settings`). Do **not** use a service-role **SQL** session for ordinary admin HTTP handlers (only background jobs use that connection).
- **`DELETE /users/me`:** cascade app rows with the **user** DB session; delete the **Auth user** via **Supabase Admin API** (service key), not `get_admin_session` for dashboard-style routes.
- Schema: **Supabase migrations** (`supabase/migrations/`), not `uv run dbreset` as the primary model. Multi-tenant testing: see **Testing** above.
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
| Globale Filter-Regeln, Scraper-Einstellungen | `AppSettings` | Nur Admins (UI + DB: RLS, siehe Schritt 6) |
| Benachrichtigungskanal, Mindest-Score, Modus | `UserSettings` | User |

---

## Auth-Screens & Account-Management

### UX-Stil der Auth-Screens

Die Auth-Screens liegen in einer eigenen Route-Group `(auth)` — ohne Sidebar, aber mit identischer visueller Sprache wie die App:

- **Hintergrund:** `gradient-subtle` (minimal amber-getönter Off-White-Hintergrund)
- **Theme-Farbe:** Amber (`#F59E0B`) — primärer Button, Focus-Ring
- **Font:** Lexend (wie die App)
- **Card:** shadcn/ui `Card` — `max-w-sm`, zentriert vertikal/horizontal
- **Logo:** Schnappster-Branding + Icon oberhalb der Card
- **Sprache:** Deutsch
- **Feedback:** `toast.error` bei Fehlern, Success → direkt weiterleiten (kein separater Toast)

### Screen-Übersicht

| Screen | Route | Beschreibung |
|---|---|---|
| **Login** | `/login` | Social-Login-Buttons + E-Mail/Passwort-Formular |
| **Registrierung** | `/register` | E-Mail/Passwort-Formular + Social-Login |
| **Passwort vergessen** | `/forgot-password` | E-Mail eingeben → Reset-Link per E-Mail |
| **Passwort zurücksetzen** | `/reset-password` | Neues Passwort setzen (via Supabase-Reset-Token in URL) |

### Login-Screen (`/login`)

Aufbau (von oben nach unten innerhalb der Card):
1. **Social Login:** „Mit Google anmelden" + „Mit Facebook anmelden" (volle Breite)
2. **Divider:** „oder"
3. **Formular:** E-Mail + Passwort
4. **Link:** „Passwort vergessen?" → `/forgot-password` (rechts ausgerichtet, `text-link`)
5. **Button:** „Anmelden" (primary, volle Breite)
6. **Footer-Link:** „Noch kein Konto? Jetzt registrieren" → `/register`

Nicht eingeloggte User werden bei jedem App-Aufruf automatisch zu `/login` weitergeleitet.

### Registrierungs-Screen (`/register`)

- Social-Login-Buttons (Google, Facebook) (volle Breite)
- Divider: „oder"
- Formular: E-Mail + Passwort + Passwort bestätigen
- Button: „Registrieren" (primary, volle Breite)
- Link: „Bereits ein Konto? Jetzt anmelden" → `/login`

### Passwort vergessen / zurücksetzen

**Forgot-Password (`/forgot-password`):**
- E-Mail-Feld + Button „Reset-Link anfordern"
- Nach Absenden immer dieselbe neutrale Bestätigung: „Falls ein Account mit dieser E-Mail existiert, wurde eine E-Mail verschickt." (kein User-Enumeration)
- Supabase Auth versendet die E-Mail automatisch

**Reset-Password (`/reset-password`):**
- Supabase fügt Token als URL-Parameter an — Supabase JS SDK verarbeitet ihn automatisch beim Seitenaufruf
- Formular: Neues Passwort + Bestätigen
- Nach Erfolg: Weiterleitung zu `/login` mit Toast: „Passwort wurde geändert"

### Passwort ändern (User-Settings-Page)

Eigener Abschnitt innerhalb der Benutzereinstellungen-Seite — **nur sichtbar für E-Mail/Passwort-User**, ausgeblendet bei reinen OAuth-Accounts (erkennbar an fehlender Passwort-Identität in Supabase Auth).

- Felder: Neues Passwort + Bestätigen
- Kein „altes Passwort"-Feld (Supabase Auth erlaubt direkte Änderung nach Login)
- Button: „Passwort ändern"

### Konto löschen (User-Settings-Page)

Am Ende der Settings-Page als eigenständiger **Danger Zone**-Abschnitt:

- Separierte Card mit rotem Akzent (`border-destructive/30`, `CardTitle` in `text-destructive`)
- Beschreibungstext: „Dein Konto und alle gespeicherten Daten (Suchen, Schnäppchen) werden unwiderruflich gelöscht."
- Button: „Konto löschen" (`variant="destructive"`, outline-style um versehentliche Klicks zu vermeiden)
- **Bestätigung:** shadcn/ui `AlertDialog` — Titel „Konto wirklich löschen?", Bestätigungs-Button erst klickbar nach Eingabe des Wortes `löschen` in ein Textfeld
- **Backend-Logik:** App-Tabellen mit User-Session/RLS kaskadieren → Supabase-Auth-User per **Admin API** (Service-Role-Key), siehe „Verbindliche Festlegung“
- **Schutz Haupt-Admin:** Der primäre Admin-Account soll **eindeutig** erkennbar sein (**eine** Quelle festlegen: z. B. nur `PRIMARY_ADMIN_EMAIL` in `.env` **oder** nur DB-Flag — nicht beides widersprüchlich). Dieser Account kann sich nicht selbst löschen — API `403`, Frontend Hinweis

---

## Impressum

In Deutschland gesetzlich vorgeschrieben (TMG § 5). Als einfache statische Seite umsetzen:

- Route: `/impressum` — eigene Next.js-Page, kein API-Aufruf
- Inhalt: Name + Anschrift, E-Mail-Adresse, ggf. Umsatzsteuer-ID
- Link: im Sidebar-Footer (unterhalb der Navigation) und/oder im Login/Register-Screen

**Route-Platzierung:** `/impressum` soll **nicht** von einem Layout erzwungen werden, das Auth voraussetzt — bei Bedarf eigene Route-Group `(public)` oder Pfad **außerhalb** von `(app)`, damit die Middleware-Ausnahme greift und keine Sidebar-Pflicht entsteht.

```tsx
// z. B. web/app/(public)/impressum/page.tsx oder web/app/impressum/page.tsx — statisch, kein "use client" nötig
export default function ImpressumPage() {
  return (
    <div className="max-w-2xl space-y-4">
      <h1 className="text-xl font-semibold">Impressum</h1>
      <p>Angaben gemäß § 5 TMG</p>
      {/* Name, Anschrift, E-Mail */}
    </div>
  )
}
```

Die Impressum-Seite muss auch ohne Login erreichbar sein — Middleware so konfigurieren, dass `/impressum` von der Auth-Weiterleitung ausgenommen ist.

---

## Datenschutz & DSGVO

Für einen **öffentlichen SaaS-Betrieb** in der EU/DE sind Impressum allein nicht ausreichend.

### Datenschutzerklärung

- Route: **`/datenschutz`** — statische Next.js-Page (wie Impressum), **ohne Login** erreichbar
- Inhalt (Mindestpunkte, mit Rechtsberatung abstimmen): Verantwortlicher, Zwecke der Verarbeitung, Rechtsgrundlagen, **Supabase** (Auth/DB-Hosting), ggf. **OpenRouter/AI-Anbieter** (wenn personenbezogene Inhalte aus Anzeigen verarbeitet werden), Cookies/localStorage falls genutzt, Speicherdauer, Betroffenenrechte (Auskunft, Löschung — Konto-Löschung in der App verlinken), Beschwerderecht bei Aufsichtsbehörde
- Links: Sidebar-Footer, Login/Register, ggf. Footer der Auth-Card
- Middleware: `/datenschutz` von Auth-Redirect **ausnehmen** (wie `/impressum`)

### Auftragsverarbeitung (AVV)

- Mit **Supabase** einen **Data Processing Agreement (DPA)** / Auftragsverarbeitungsvertrag abschließen (Organisation im Dashboard → Legal, Übersicht unter [supabase.com/legal](https://supabase.com/legal) — exakten Prozess mit aktueller Doku abgleichen)
- Weitere Subprozessoren (E-Mail-Versand, Sentry, Hosting) dokumentieren und in der Datenschutzerklärung nennen
- Bei Nutzung von **US-Anbietern** ohne angemessenes Schutzniveau: **Standardvertragsklauseln** und ggf. TIA — rechtlich klären

### Technische Hinweise

- **Konto-Löschung** (bereits geplant) als Ausübung des Löschrechts Art. 17 dokumentieren
- **Telegram Chat-ID** in `UserSettings` ist personenbezogen — in der Datenschutzerklärung erwähnen

---

## Frontend-Auth: Session, Refresh, Token-Speicher

Next.js und FastAPI teilen sich die Verantwortung: das **Frontend** hält die Supabase-Session, das **Backend** validiert das Access-Token pro Request.

### Supabase JS (`@supabase/supabase-js`)

- Client mit `SUPABASE_URL` + **`anon` key** initialisieren (nie Service-Role im Browser)
- **`onAuthStateChange`** nutzen, um Session-Wechsel (Login, Logout, Token-Refresh) in React-State oder Context zu spiegeln
- **Refresh:** Supabase-Client erneuert Access-Tokens **automatisch** mit dem Refresh-Token, solange die Session lebt — keine eigene Refresh-Logik duplizieren, außer es gibt besondere Anforderungen

### Token an die FastAPI-API senden

- API-Calls (z. B. `fetch` in `web/lib/api.ts`): **`Authorization: Bearer <access_token>`** aus der aktuellen Supabase-Session setzen
- Bei **gleichem Origin** (Caddy: UI und `/api` unter einer Domain) entfallen viele CORS-Probleme; trotzdem konsistent den Header mitsenden

### Speicherort der Session

| Ansatz | Kurzbeschreibung | Hinweis |
|--------|------------------|---------|
| **Standard Supabase Browser-Client** | Typisch: **localStorage** (Default) oder konfigurierbar | Einfach; bei XSS-Risiko Session-Hijacking möglich — CSP, sichere Dependencies, keine unsicheren `dangerouslySetInnerHTML` |
| **Cookie-basiert (httpOnly)** | Session/Token in **httpOnly-Cookies** — oft über **Supabase SSR** / `@supabase/ssr` + Server Components / Route Handlers | Weniger XSS-Angriffsfläche für Token-Diebstahl; mehr Setup (Middleware, Cookie-Refresh) |

**Empfehlung:** Für eine Dashboard-App mit Fokus auf schnelle Umsetzung zunächst **Standard-Client + Bearer-Header**; Migration auf **SSR/Cookies** erwägen, wenn ihr härtere Security-Anforderungen oder SEO für geschützte Bereiche braucht.

### Session-Ablauf & UX

- Abgelaufene Session: API antwortet **401** — Client soll auf **`/login`** leiten oder `signIn` anbieten
- Optional: stiller Refresh vor API-Calls, wenn `session.expires_at` nahe ist (Supabase macht oft schon genug)

### Middleware (Next.js)

- Geschützte Routen: Session aus Cookie **oder** aus lesbarem Storage prüfen — je nach gewähltem Muster; bei reinem localStorage kann Middleware die Session **ohne** zusätzlichen Trick nicht lesen → dann **Client-Guard** + ggf. kurzer Flash, oder Umstieg auf **SSR-Cookie-Session** für echtes serverseitiges Routing
- Dokumentieren, welches Muster ihr wählt, damit keine Lücke zwischen „Middleware denkt ausgeloggt“ und „Client hat noch Session“ entsteht

---

## Supabase-Integration: Schritt für Schritt

### Zwei Projekte, Umgebungen & Tests

| Nutzung | Datenbank / Auth | Zweck |
|---|---|---|
| **Lokale Entwicklung (manuell)** | `schnappster-dev` (Cloud) | Bequem: RLS, Auth, E-Mail ohne lokalen Supabase-Docker |
| **pytest (Standard)** | PostgreSQL lokal oder CI-Postgres; **Auth gemockt** | Schnell, reproduzierbar, kein Zugriff auf Prod |
| **RLS-/Auth-Integration (optional)** | `npx supabase start` **oder** isoliertes Supabase-Projekt | Policies mit echtem `auth.uid()` / JWT testen |
| **Produktion** | `schnappster-prod` | Live — **nie** für automatisierte Tests |

**Klarstellung:** „Tests mocken die DB“ ist **so nicht gemeint**. Üblich ist: **`get_current_user` / Supabase Auth mocken**, die **PostgreSQL-Verbindung** aber **real** halten (sonst fehlen echte SQL-/ORM-Tests). Nur wenn ein Test bewusst **ohne** DB läuft (reine Logik), wird die Session ersetzt oder gar nicht geöffnet.

**Postgres vs. SQLite für pytest:** Sobald die App nur noch gegen **Postgres** läuft, brauchen DB-Tests **Postgres** (lokal oder in CI). **SQLite als Ersatz** für dieselbe Suite ist **nicht empfohlen** (Dialekt, RLS, Treiber). Ausnahme: einzelne Tests **ohne** DB-Zugriff. Nach der Migration: die gleichen Regeln in **`AGENTS.md`** festhalten (nicht nur hier).

Lokale Entwicklung **kann** die Online-`schnappster-dev`-DB nutzen — das schließt aus, dass pytest dieselbe Strategie braucht.

---

### Schritt 1 — Supabase-Projekte anlegen

1. [supabase.com](https://supabase.com) → Dashboard → **New Project**
2. Projekt `schnappster-dev` anlegen (Region wählen, DB-Passwort notieren)
3. Projekt `schnappster-prod` anlegen (gleiche Region)

Für **jedes** Projekt folgende Werte notieren (Settings → API und Settings → Database):

| Wert | Wo zu finden |
|---|---|
| **Project URL** | Settings → API → Project URL |
| **anon key** | Settings → API → Project API keys |
| **service_role key** | Settings → API → Project API keys (geheim — nie ins Frontend oder Repo) |
| **Database URL** | Settings → Database → Connection string → URI (mit `[YOUR-PASSWORD]` ersetzen) |

---

### Schritt 2 — Umgebungsvariablen konfigurieren

`.env` (lokale Entwicklung, nicht ins Repo):
```env
# Supabase dev-Projekt
SUPABASE_URL=https://<dev-ref>.supabase.co
SUPABASE_ANON_KEY=<dev-anon-key>
SUPABASE_SERVICE_ROLE_KEY=<dev-service-role-key>
DATABASE_URL=postgresql://postgres:<password>@db.<dev-ref>.supabase.co:5432/postgres
```

Produktion (Server-Umgebungsvariablen oder Secrets-Manager):
```env
SUPABASE_URL=https://<prod-ref>.supabase.co
SUPABASE_ANON_KEY=<prod-anon-key>
SUPABASE_SERVICE_ROLE_KEY=<prod-service-role-key>
DATABASE_URL=postgresql://postgres:<password>@db.<prod-ref>.supabase.co:5432/postgres
```

`.env` in `.gitignore` eintragen — `SUPABASE_SERVICE_ROLE_KEY` darf das Repo nie verlassen.

---

### Schritt 3 — Python-Abhängigkeiten

```bash
uv add supabase asyncpg
```

- `supabase` — supabase-py für Auth-Operationen (JWT-Validierung, User-Management)
- `asyncpg` — asynchroner PostgreSQL-Treiber für SQLAlchemy

> **Hinweis:** supabase-py hat weniger Community-Coverage als der JS-Client. Für die aktuelle API immer **Context7** verwenden.

---

### Schritt 4 — DB-Engine auf PostgreSQL umstellen

`app/core/db.py` anpassen:

- `DATABASE_URL` aus Pydantic Settings lesen (statt SQLite-Pfad via `get_app_root()`)
- SQLAlchemy-Engine mit PostgreSQL-URL und `asyncpg`-Treiber erstellen
- `create_all(engine)` entfernt — Tabellen werden via Supabase-Migrations angelegt (Schritt 5)

Der SQLite-spezifische Code (`data/schnappster.db`, `get_app_root()`) fällt komplett weg.

---

### Schritt 5 — DB-Schema anlegen (Greenfield)

Es gibt **keine wichtigen Bestandsdaten** in SQLite, die übernommen werden müssen — Schema in Postgres **neu aufsetzen**, alte lokale SQLite-Datei kann entfallen.

**Einmalig — dev-Projekt:**

Im Supabase Dashboard → **SQL Editor** Tabellen anlegen (Namen an euer SQLModel-Schema anpassen; Beispiel):

```sql
-- Beispiel: neue Tabellen mit owner_id (kein ALTER aus SQLite-Migration nötig)
CREATE TABLE ad_search (
    id SERIAL PRIMARY KEY,
    -- ... übrige Spalten wie im SQLModel ...
    owner_id UUID NOT NULL REFERENCES auth.users(id)
);

CREATE TABLE ad (
    id SERIAL PRIMARY KEY,
    -- ... übrige Spalten wie im SQLModel ...
    owner_id UUID NOT NULL REFERENCES auth.users(id)
);

-- Globale App-Konfiguration — nur Admins (RLS in Schritt 6)
CREATE TABLE app_settings (
    id SERIAL PRIMARY KEY,
    -- ... Spalten wie im SQLModel ...
    singleton_guard INTEGER UNIQUE DEFAULT 1  -- optional: eine Zeile erzwingen
);

CREATE TABLE user_settings (
    user_id UUID PRIMARY KEY REFERENCES auth.users(id),
    display_name TEXT,
    telegram_chat_id TEXT,
    notify_telegram BOOLEAN DEFAULT FALSE,
    notify_email BOOLEAN DEFAULT FALSE,
    notify_web_push BOOLEAN DEFAULT FALSE,
    notify_min_score INTEGER DEFAULT 5,
    notify_mode TEXT DEFAULT 'instant'
);
```

> Die konkreten Spalten und Typen müssen **1:1** zu euren SQLModel-Definitionen passen; obiges SQL ist eine **Strukturskizze**, kein Copy-Paste ohne Abgleich.

Dasselbe Schema anschließend im **prod**-Projekt ausrollen (Migration / SQL Editor).

Zukünftige Schema-Änderungen: Supabase CLI `supabase migration new …` → SQL unter **`supabase/migrations/`** versionieren → dev anwenden/testen → prod deployen (nicht nur lose `migrations/` im Repo ohne CLI-Pfad, es sei denn, ihr mappt das bewusst).

---

### Schritt 6 — RLS Policies einrichten

Im SQL Editor (dev zuerst, dann prod):

```sql
-- RLS aktivieren
ALTER TABLE ad_search ENABLE ROW LEVEL SECURITY;
ALTER TABLE ad ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE app_settings ENABLE ROW LEVEL SECURITY;

-- Policies: jeder User sieht und verändert nur seine eigenen Daten
CREATE POLICY "users_own_searches" ON ad_search
    FOR ALL USING (auth.uid() = owner_id) WITH CHECK (auth.uid() = owner_id);

CREATE POLICY "users_own_ads" ON ad
    FOR ALL USING (auth.uid() = owner_id) WITH CHECK (auth.uid() = owner_id);

CREATE POLICY "users_own_settings" ON user_settings
    FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

-- app_settings: nur Admins (User-JWT + RLS — verbindliche Architektur, siehe „Verbindliche Festlegung“)
-- Erfordert role in JWT app_metadata (wie in Schritt 10)
CREATE POLICY "admins_own_app_settings" ON app_settings
    FOR ALL TO authenticated
    USING ((auth.jwt() -> 'app_metadata' ->> 'role') = 'admin')
    WITH CHECK ((auth.jwt() -> 'app_metadata' ->> 'role') = 'admin');
```

Es gibt **nur eine** Policy auf `app_settings` (für `authenticated`). Ihre `USING`-Bedingung ist nur für JWTs mit `app_metadata.role = 'admin'` erfüllt — **alle anderen** eingeloggten User sehen damit **keine** Zeilen (kein separater „Deny“ nötig).

Testen im SQL Editor mit `SET LOCAL role = authenticated; SET LOCAL request.jwt.claims = '{"sub": "<uuid>"}';` vor einer SELECT-Abfrage — für Admin-Policy-Tests `app_metadata` im JWT-JSON ergänzen (z. B. `"app_metadata":{"role":"admin"}`), sonst schlägt `auth.jwt() -> …` fehl.

**Wichtig für FastAPI:** Damit `auth.uid()` und `auth.jwt()` in Policies greifen, muss jede **User-Session** vor SQL die **JWT-Claims** an Postgres übergeben (z. B. `SET LOCAL request.jwt.claims` / `SET LOCAL role` — exakte Syntax mit asyncpg/SQLAlchemy per **Context7** zum aktuellen Supabase-Empfehlungspfad). Ohne das sieht RLS den Nutzer nicht und blockiert zu viel oder falsch.

---

### Schritt 7 — OAuth-Provider aktivieren

**Google:**
1. [console.cloud.google.com](https://console.cloud.google.com) → Credentials → OAuth 2.0 Client ID erstellen
2. Authorized redirect URIs: `https://<dev-ref>.supabase.co/auth/v1/callback` (+ prod-URL)
3. Supabase Dashboard → Authentication → Providers → Google → Client ID + Secret eintragen

**Facebook:**
1. [developers.facebook.com](https://developers.facebook.com) → App erstellen → Facebook Login aktivieren
2. Valid OAuth Redirect URIs: `https://<dev-ref>.supabase.co/auth/v1/callback`
3. Supabase Dashboard → Authentication → Providers → Facebook → App ID + Secret eintragen

**Site URL konfigurieren** (Authentication → URL Configuration):
- Site URL: `http://localhost:3000` (dev) bzw. `https://schnappster.app` (prod)
- Redirect URLs: beide URLs eintragen

---

### Schritt 8 — FastAPI: JWT-Validierung und `get_current_user`

```python
# app/core/auth.py — schematisch, aktuellen Code mit Context7 generieren
from supabase import create_client

supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)

async def get_current_user(token: str = Depends(oauth2_scheme)):
    response = supabase.auth.get_user(token)
    if not response.user:
        raise HTTPException(status_code=401, detail="Nicht autorisiert")
    return response.user  # enthält id, email, user_metadata

async def require_admin(user = Depends(get_current_user)):
    if user.app_metadata.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin-Zugriff erforderlich")
    return user
```

**Abgleich: JWT, `require_admin`, supabase-py und RLS**

- Die **Rolle `admin`** muss in Supabase in **`app_metadata`** (nicht `user_metadata`) liegen — nur dann steuert der Server sie vertrauenswürdig; `user_metadata` ist vom Client überschreibbar.
- **`require_admin`** im Python-Code muss dieselbe Quelle lesen wie die RLS-Policy in Schritt 6 (`auth.jwt() -> 'app_metadata' ->> 'role'`). Das **supabase-py**-`User`-Objekt nutzt typischerweise **`user.app_metadata`** (Python-Attribut) — **Feldnamen und Verschachtelung** mit der aktuellen Library-Version und eurem JWT per **Context7 / offizielle Doku** abgleichen; nach Updates erneut prüfen.
- **`get_user(token)`** (Beispiel oben) kann je nach Version/Setup **Netzwerk** bedeuten — für Produktion **lokale JWT-Signatur** (JWKS) erwägen, um Latenz und Supabase-Abhängigkeit pro Request zu reduzieren (optional, eigener Task).
- Strikte Regel: Wenn `app_metadata.role` im JWT fehlt oder abweicht, muss **`require_admin`** **403** liefern und die DB-Policy ebenfalls **keinen** Admin-Zugriff gewähren.

---

### Schritt 9 — Zwei DB-Sessions implementieren

**User-Context (`get_db_session`):** JWT-Claims werden als PostgreSQL-Session-Variable gesetzt → `auth.uid()` gibt die User-ID zurück → RLS filtert automatisch.

**Admin-Context (`get_admin_session`):** Verbindung mit `SUPABASE_SERVICE_ROLE_KEY` → RLS ist bypassed → `owner_id` in alle Queries und Inserts explizit schreiben. **Nur** für **Background-Jobs**. **Admin-HTTP-Routen** nutzen **ausschließlich** `get_db_session()` nach `require_admin` — siehe **„Verbindliche Festlegung: Admin-HTTP = Variante B“** oben.

> Für die konkrete Implementierung mit asyncpg + SQLAlchemy Events (SET LOCAL request.jwt.claims) **Context7 verwenden** — supabase-py ändert hier regelmäßig die empfohlene API.

---

### Schritt 10 — Admin-Rolle vergeben

Der erste Admin wird manuell über den Supabase SQL Editor zugewiesen:

```sql
-- App-Metadaten setzen (nicht vom User überschreibbar)
UPDATE auth.users
SET raw_app_meta_data = raw_app_meta_data || '{"role": "admin"}'::jsonb
WHERE email = 'admin@example.com';
```

Das JWT enthält danach `app_metadata.role = "admin"` — FastAPI prüft das in `require_admin`.

Weitere Admins: gleicher SQL-Befehl, oder eigenes Admin-Interface in Phase 4.

---

### Schritt 11 — Unit-Tests: Supabase mocken

**Auth** mocken — **kein** Aufruf von Supabase Cloud, **keine** Produktions-DB. **Postgres für DB-Tests** weiterhin nötig (lokal/CI), sofern der Test echtes SQL ausführt (siehe Abschnitt „Zwei Projekte, Umgebungen & Tests“).

```python
# tests/conftest.py
from fastapi.testclient import TestClient
from app.main import app
from app.core.auth import get_current_user

@pytest.fixture
def mock_user():
    # id als gültige UUID, wenn Tests echte Postgres-FKs treffen
    return SimpleNamespace(
        id="550e8400-e29b-41d4-a716-446655440000",
        email="test@test.com",
        app_metadata={"role": "user"},
    )

@pytest.fixture(autouse=True)
def override_auth(mock_user):
    app.dependency_overrides[get_current_user] = lambda: mock_user
    yield
    app.dependency_overrides.clear()
```

Für DB-Assertions: **PostgreSQL** (Docker, `pytest-postgresql`, CI-Service). **Nicht** SQLite als Ersatz für die Postgres-Ziel-Architektur. Für RLS-Tests: Supabase-Umgebung (lokal oder Integrationstest).

---

## Deployment

### Warum Frontend und Backend trennen?

Der aktuelle Ansatz (Next.js als Static Export, durch FastAPI ausgeliefert) hat mit der SaaS-Umstellung einen entscheidenden Nachteil: **`middleware.ts` funktioniert nur im Node.js-Modus** — nicht beim Static Export. Ohne Middleware können nicht eingeloggte User nicht server-seitig auf `/login` umgeleitet werden; der Redirect passiert erst im Browser (sichtbarer Flash, schlechtere UX, kein sicheres Route-Guarding).

Gleichzeitig macht die Trennung auch operativ mehr Sinn: FastAPI macht reines API, Next.js macht reines Frontend, Caddy schaltet als Reverse Proxy davor.

### Ziel-Architektur

```
Internet → Caddy (Port 80/443, TLS automatisch)
              │
              ├── /api/*  → FastAPI    (Port 8000, Python)
              └── /*      → Next.js   (Port 3000, Node.js)
```

Alle drei Dienste laufen als Docker-Container, verwaltet mit Docker Compose.

### Was sich ändert

**`web/next.config.mjs`** — Static Export entfernen:
```js
// Vorher:
...(process.env.NODE_ENV === "production" && { output: "export" }),
trailingSlash: true,

// Nachher: beides entfernen — Next.js läuft als Node.js-Server
// images.unoptimized: true kann bleiben (oder entfernen für optimierte Images)
```

**`app/core/bootstrap.py`** — Frontend-Serving entfernen:
```python
# Entfernen:
app.include_router(frontend_router)  # war Fallback für Dynamic Routes
mount_frontend(app)                  # war StaticFiles für web/out/
```

FastAPI wird damit ein reiner API-Server. Der `frontend_router` und `mount_frontend` können aus `app/routes/` gelöscht werden.

### Docker Compose

**`Dockerfile`** (FastAPI, im Repo-Root):
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN pip install uv && uv sync --frozen --no-dev
COPY . .
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**`web/Dockerfile`** (Next.js):
```dockerfile
FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build
CMD ["npm", "start"]
```

**`docker-compose.yml`** (Repo-Root):
```yaml
services:
  api:
    build: .
    restart: unless-stopped
    env_file: .env

  web:
    build: ./web
    restart: unless-stopped
    env_file: ./web/.env.local
    environment:
      - NEXT_PUBLIC_API_URL=  # leer = same origin (Caddy routet /api/*)

  caddy:
    image: caddy:alpine
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile
      - caddy_data:/data
    depends_on:
      - api
      - web

volumes:
  caddy_data:
```

**`Caddyfile`** (Repo-Root):
```
schnappster.app {
    handle /api/* {
        reverse_proxy api:8000
    }
    handle {
        reverse_proxy web:3000
    }
}
```

Caddy besorgt TLS-Zertifikate von Let's Encrypt automatisch — kein Certbot, kein manuelles Renewals.

**API-Pfad: Caddy und FastAPI abstimmen:** Caddy leitet **`/api/*`** unverändert an den API-Container weiter (z. B. Request-Pfad bleibt `/api/v1/...`). Das FastAPI-Routing muss **dieselben Pfade** bedienen — z. B. `APIRouter(prefix="/api")` bzw. globales Prefix, **oder** Caddy `handle_path` / `uri strip_prefix` nutzen und Backend ohne `/api`-Prefix. Vor dem Umbau festlegen und `NEXT_PUBLIC_API_URL` (leer = gleiche Origin-URLs mit `/api`) konsistent halten.

**CORS (Cross-Origin Resource Sharing)**

- **Produktion mit Caddy (ein Host):** Browser ruft `https://schnappster.app` und `https://schnappster.app/api/...` auf — **gleiche Origin**, klassisches CORS für API-Calls meist **nicht** nötig (kein Preflight für einfache GET ohne exotische Header; bei `Authorization` kann dennoch Preflight entstehen — FastAPI `CORSMiddleware` mit erlaubtem Origin `https://schnappster.app` schadet nicht).
- **Abweichende Origins** treten auf bei: lokalem **Next** auf `http://localhost:3000` und API auf `http://localhost:8000`, **Staging** mit anderer Domain, oder **Vorschau-Deployments**. Dann in FastAPI **`CORSMiddleware`** konfigurieren:
  - `allow_origins`: explizite Liste (kein `*` mit Credentials)
  - `allow_credentials`: `true` nur wenn nötig (Cookies cross-origin)
  - `allow_methods` / `allow_headers`: mindestens `Authorization`, `Content-Type`
- **Umgebungsvariablen:** z. B. `CORS_ORIGINS=https://app.example.com,https://staging.example.com` aus `.env` lesen — nie Wildcards in Prod mit sensiblen Daten.
- **OPTIONS**-Preflight: sicherstellen, dass Caddy **OPTIONS** an FastAPI durchreicht und nicht abblockt.

### Hosting-Optionen

| Option | Kosten | Ressourcen | Server | Empfohlen für |
|---|---|---|---|---|
| **Eigener T640** | kostenlos | sehr viel | lokal/Büro | Entwicklung, Hobby, Testen |
| **Oracle Cloud Free Tier** | kostenlos | 4 ARM-Cores, 24 GB RAM | EU verfügbar | Produktion gratis |
| **Hetzner CX33** | ~€7/mo | 4 vCPU, 8 GB | DE (DSGVO) | Produktion, zuverlässig |
| **Railway / Render** | ~€15–30/mo | managed | US-Server | Zero-Ops, kein Serverbetrieb |

**Oracle Cloud Free Tier** ist die stärkste kostenlose Option — die Always-Free-ARM-Instanzen (Ampere A1) sind dauerhaft gratis, keine Kreditkarte nach Ablauf. Achtung: Signup kann Kreditkarte zur Verifikation verlangen. Ressourcen (4 Cores, 24 GB) sind für Schnappster weit überdimensioniert.

**Eigener T640**: Hardware-Kosten entfallen. Voraussetzungen: Router-Portweiterleitung (80, 443), DynDNS falls keine statische IP (DuckDNS — kostenlos), Strom läuft natürlich.

### Docker vs. direkt (systemd)

Docker Compose ist sinnvoll für Cloud-VPS (reproduzierbar, Wechsel zwischen Servern einfach). Für einen eigenen Server mit einem Entwickler ist **systemd direkt oft einfacher und leichtgewichtiger**:

| | systemd direkt | Docker Compose |
|---|---|---|
| **Setup-Aufwand** | niedrig | mittel |
| **Ressourcen-Overhead** | minimal | etwas mehr |
| **Updates** | `git pull + systemctl restart` | `docker compose up --build` |
| **Isolation** | keine | vollständig |
| **Reproduzierbar** | nein | ja |
| **Ideal für** | T640, einzelner Server | Cloud-VPS, mehrere Server |

**Empfehlung:**
- **T640 / eigener Server** → systemd direkt (kein Docker)
- **Oracle Cloud / Hetzner** → Docker Compose (Dockerfiles aus vorherigem Abschnitt)

### Deployment auf dem T640 (systemd, kein Docker)

```bash
# Einmalig: Abhängigkeiten
apt install caddy nodejs npm -y
curl -LsSf https://astral.sh/uv/install.sh | sh

# Repo klonen
git clone https://github.com/pikktee/schnappster.git /opt/schnappster
cd /opt/schnappster
cp .env.example .env    # Credentials eintragen

# systemd-Service für FastAPI: /etc/systemd/system/schnappster-api.service
[Unit]
Description=Schnappster API
After=network.target

[Service]
WorkingDirectory=/opt/schnappster
ExecStart=/root/.cargo/bin/uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
Restart=always
EnvironmentFile=/opt/schnappster/.env

[Install]
WantedBy=multi-user.target

# systemd-Service für Next.js: /etc/systemd/system/schnappster-web.service
[Service]
WorkingDirectory=/opt/schnappster/web
ExecStart=/usr/bin/npm start
Restart=always

# Starten
systemctl daemon-reload
systemctl enable --now schnappster-api schnappster-web

# Caddyfile: /etc/caddy/Caddyfile — wie oben beschrieben
systemctl reload caddy
```

**DynDNS falls keine statische IP** (DuckDNS — kostenlos):
```bash
# Cronjob alle 5 Minuten: IP aktualisieren
*/5 * * * * curl -s "https://www.duckdns.org/update?domains=<subdomain>&token=<token>&ip="
```

**Updates:**
```bash
cd /opt/schnappster && git pull
systemctl restart schnappster-api
cd web && npm run build && systemctl restart schnappster-web
```

### Deployment auf Cloud-VPS (Docker Compose)

```bash
# Einmalig: Server einrichten
ssh root@<server-ip>
apt install docker.io docker-compose-plugin -y

# Repo klonen + starten
git clone https://github.com/pikktee/schnappster.git /opt/schnappster
cd /opt/schnappster
cp .env.example .env    # Credentials eintragen
docker compose up -d

# Update deployen
git pull && docker compose up -d --build
```

Für automatisches Deployment: GitHub Actions Workflow, der nach Push auf `main` per SSH `git pull && docker compose up -d --build` auf dem Server ausführt.

### Lokale Entwicklung

Nach Entfernen des Static Exports weiter mit getrennten Prozessen (wie bisher üblich):
```bash
uv run start --dev          # oder API nur: uvicorn … — je nach pyproject-Skript
cd web && npm run dev       # Next.js auf :3000, Proxy /api/* → :8000
```

**Hinweis:** Sobald `output: "export"` entfällt, prüfen, ob `uv run start` (ohne `--dev`) noch sinnvoll ist — Produktions-Compose nutzt `npm run build` + `npm start` für Next; lokal ist **`--dev` / `npm run dev`** der Referenz-Workflow. Caddy/Docker lokal nicht nötig.

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
- User-Management-Dashboard spart eigene Admin-Routen für User-CRUD
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

**Praktische Umsetzung (verbindlich):**
- **Alle HTTP-Routen** (User und Admin): `get_db_session()`, JWT gesetzt, **RLS aktiv** — für Mandanten-Daten kein `WHERE owner_id = …` nötig
- **Hintergrundprozesse** (Scraper, Analyzer): `get_admin_session()` + explizites Setzen von `owner_id` in Code
- **Admin-HTTP** (Logs, App-Settings, Stats, manuelle Trigger): immer **`require_admin` + RLS-Policies** für `role = 'admin'` (Schritt 6-Muster); **kein** `get_admin_session()` in diesen Handlern
- **Querschnitt durch alle Mandanten** (z. B. `/admin/stats`): **zusätzliche RLS-Policies** für Admins auf den betroffenen Tabellen **oder** **SQL-Aggregat-Funktion** mit `SECURITY DEFINER` (nur Zahlen) — weiterhin **ohne** Service-Role-HTTP

### Admin-HTTP: Variante B (festgelegt, keine Alternative A)

**Variante B** ist die **einzige** vorgesehene Variante für Admin-Dashboard und alle Admin-API-Routen: Der Admin bleibt mit **normalem User-JWT** an der DB; RLS bleibt aktiv; zusätzliche Policies erteilen Rechte für `app_metadata.role = 'admin'` (siehe Schritt 6 für `app_settings`).

**Variante A** (HTTP-Handler öffnen eine Service-Role-Connection und umgehen RLS) ist für Schnappster **bewusst nicht vorgesehen** — höheres Risiko bei falscher Route-zu-Session-Zuordnung.

### Warum PostgreSQL statt SQLite?

SQLite ist single-writer — bei mehreren gleichzeitigen Usern die Suchen auslösen
kommt es zu Write-Locks. PostgreSQL ist für concurrent access gebaut.
Durch Supabase entsteht kein zusätzlicher Ops-Aufwand für den DB-Server.

---

## Detaillierter Umsetzungsplan

### Phase 1 — Backend: Auth & Multi-Tenancy

**Deployment-Vorbereitung (einmalig):**
- `web/next.config.mjs`: `output: 'export'` und `trailingSlash` entfernen
- `app/core/bootstrap.py`: `frontend_router` und `mount_frontend` entfernen
- `Dockerfile`, `web/Dockerfile`, `docker-compose.yml`, `Caddyfile` anlegen

**Supabase-Setup (einmalig, manuell):**
- Projekte `schnappster-dev` und `schnappster-prod` auf supabase.com anlegen
- OAuth-Provider aktivieren: Google + Facebook (Redirect URLs konfigurieren)
- `.env` mit dev-Credentials befüllen

**Backend-Migration:**
- `uv add supabase asyncpg`
- `app/core/db.py`: SQLite-Engine durch PostgreSQL-Engine ersetzen (`DATABASE_URL` aus Settings)
- Pydantic Settings um `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `DATABASE_URL` erweitern
- `app/core/auth.py`: `get_current_user` + `require_admin` Dependencies implementieren (supabase-py, **Context7 nutzen** — siehe Schritt 8 „Abgleich JWT“)
- `get_db_session()` (User-Context, RLS aktiv — **alle HTTP-Routen inkl. Admin**) und `get_admin_session()` (Service-Role — **nur Jobs**) implementieren
- Optional früh: **`CORSMiddleware`** + `CORS_ORIGINS` für lokales `localhost:3000` ↔ `localhost:8000`, siehe **Deployment → CORS**

**DB-Schema:**
- Postgres-Schema **neu** anlegen (Greenfield, kein SQLite-Datenimport)
- `owner_id` auf `AdSearch` und `Ad`; `UserSettings`; `AppSettings`
- RLS aktivieren: User-Tabellen pro Besitzer; `app_settings` nur für Admins (Schritt 6)
- Hintergrundjobs (ScraperService, AIService) auf `get_admin_session` + explizites `owner_id` umstellen

**Tests:**
- `conftest.py`: `get_current_user` Override für Unit-Tests, separates Admin-Fixture
- Bestehende Tests auf PostgreSQL-kompatible Fixtures umstellen
- `uv run pytest` muss grün sein

---

### Phase 2 — Frontend: Auth-Screens

**Impressum & Datenschutz anlegen:**
- `/impressum` und **`/datenschutz`** als statische Next.js-Pages (kein API-Aufruf), siehe Abschnitte **Impressum** und **Datenschutz & DSGVO**
- Links im Sidebar-Footer, Login/Register
- Middleware: **`/impressum`**, **`/datenschutz`** (und ggf. weitere öffentliche Seiten) von Auth-Weiterleitung ausnehmen

**Route-Group `(auth)` anlegen** (`web/app/(auth)/`):
- Gemeinsames Layout ohne Sidebar: `gradient-subtle`-Hintergrund, Logo + `Card max-w-sm` zentriert
- `/login`: Social-Login-Buttons (Google, Facebook) + E-Mail/Passwort-Formular + „Passwort vergessen?"-Link
- `/register`: Social-Login-Buttons + E-Mail/Passwort/Bestätigen-Formular + Link zu `/login`
- `/forgot-password`: E-Mail-Feld, neutrale Bestätigungsmeldung nach Absenden
- `/reset-password`: Neues Passwort + Bestätigen, Token aus URL via Supabase JS SDK verarbeiten

**Auth-State im Frontend:**
- Supabase JS Client (`@supabase/supabase-js`) einrichten
- Auth-Context oder Hook (`useSession`) für Session-State
- Middleware: nicht eingeloggte User → Redirect zu `/login`
- Nach Login → Redirect zur App
- Details: Abschnitt **Frontend-Auth: Session, Refresh, Token-Speicher** (Token an API, Refresh, localStorage vs. Cookies, Middleware-Lücken vermeiden)

---

### Phase 3 — Account-Management

**User-Settings-Page erweitern** (bestehende `/settings` umbauen für Multi-User):
- Benutzerprofil-Abschnitt: Name (editierbar), Avatar (aus OAuth, read-only), E-Mail (read-only)
- Passwort-ändern-Abschnitt (nur bei E-Mail/Passwort-Accounts sichtbar): Neues Passwort + Bestätigen
- Benachrichtigungs-Einstellungen: Telegram Chat-ID, Kanal-Auswahl, Mindest-Score (Slider 0–10), Modus
- **Danger Zone:** Konto löschen — `AlertDialog` mit Eingabebestätigung (`löschen` eintippen)

**Backend:**
- `GET /users/me` + `PATCH /users/me` — Profil lesen und aktualisieren
- `GET /users/me/settings` + `PATCH /users/me/settings` — UserSettings
- `DELETE /users/me` — App-Daten mit User-Session/RLS kaskadieren, dann Auth-User per **Supabase Admin API** (Service-Role-Key); Haupt-Admin geschützt (403); siehe „Verbindliche Festlegung“
- `POST /users/me/change-password` — via Supabase Auth API

---

### Phase 4 — Admin-Bereich

**DB/Session:** Alle Admin-Endpunkte nutzen **`get_db_session()`** + **`require_admin`**; fehlende Rechte werden über **RLS-Admin-Policies** ergänzt (z. B. lesender Querschnitt für Stats) — **kein** `get_admin_session()` für HTTP.

**Logs (Speicherort klären):** Wenn Logs nur **Dateien/stdout** sind, schützt RLS nicht — Zugriff nur über **`require_admin`** in FastAPI und sichere Dateipfade/Rotation. Wenn Logs in der **DB** landen, **RLS + Admin-Policies** wie bei anderen Tabellen vorsehen.

**Bestehende Routen absichern:**
- Logs-Route: `require_admin` Dependency hinzufügen
- App-Settings-Route: `require_admin` Dependency hinzufügen

**Neue Admin-Routen:**
- `POST /admin/scrape` — Manuell Scrape auslösen (für eine oder alle AdSearches)
- `POST /admin/analyze` — Manuell AI-Analyse auslösen
- `GET /admin/stats` — System-Statistiken: User-Anzahl, Ad-Anzahl, letzte Scrape-Zeit, Analyzer-Backlog

**Frontend (Admin-Bereich in Sidebar):**
- Admin-Sektion in der Sidebar (nur sichtbar für Admins)
- Logs-Seite: bereits vorhanden, jetzt nur noch für Admins zugänglich
- Admin-Dashboard: Statistiken, manuelle Trigger-Buttons

---

### Phase 5 — Betrieb

**Benachrichtigungen:**
- Telegram: nach jedem Analyze-Run für User mit `notify_telegram = true` und `bargain_score >= notify_min_score` — via Bot-Token aus `.env`, Chat-ID aus `UserSettings`
- E-Mail: Supabase Transactional Emails oder eigener SMTP (Resend empfohlen)
- Web Push: VAPID-Keys generieren, Service Worker im Frontend, `PushSubscription` in `UserSettings` speichern

**Betrieb:**
- Rate-Limiting auf Auth-Routen (FastAPI `slowapi` oder Supabase-seitig)
- Monitoring: Sentry für Python-Backend und Next.js-Frontend
- **CORS:** bei getrennten Origins (lokal, Staging, Vorschau) `CORSMiddleware` + `CORS_ORIGINS` aus `.env`; siehe **Deployment → CORS**
- **DSGVO laufend:** Subprozessor-Liste und AVV mit Supabase (und anderen Anbietern) aktuell halten; Datenschutzerklärung bei neuen Features (z. B. neuer Analytics-Anbieter) anpassen

---

### Phase 6 — Payments (perspektivisch)

- Stripe-Subscriptions, Webhooks, Feature-Gates
- Wird erst geplant wenn Phase 5 abgeschlossen
