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
  lokales PostgreSQL — schnell, kein Netzwerk, CI-fähig
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

## Konventionen

- Schema-Änderungen: Supabase-Migrations (`supabase migration new`) — kein `uv run dbreset` mehr
- SQLModel-Muster: Tabellen-Definition + Read/Create/Update-Schemas in derselben Datei
- Background-Jobs: ScraperService und AIService haben je eine Single-Worker-Queue —
  Jobs dürfen sich nicht überlappen
- `AppSettings`-Tabelle für globale runtime-konfigurierbare Einstellungen (Admin)
- `UserSettings`-Tabelle für benutzerspezifische Einstellungen (Telegram Chat-ID, Benachrichtigungen)
- Konto-Löschung: Cascade-Delete aller User-Daten via Service-Role, danach Supabase Auth User löschen — Haupt-Admin kann sich nicht löschen (API gibt 403)
- Telegram Bot-Token in `.env` — Chat-ID je User in `UserSettings`
- Avatar kommt als URL aus der Supabase Auth Session (OAuth-Provider) — kein eigenes Storage
- Passwort-Änderung über Supabase Auth API — kein altes Passwort nötig (User ist eingeloggt)
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
- **Backend-Logik:** Cascade-Delete aller User-Daten (AdSearches, Ads, UserSettings) → anschließend Supabase Auth User löschen via Service-Role
- **Schutz Haupt-Admin:** Der primäre Admin-Account (definiert über `is_primary_admin`-Flag oder feste E-Mail in `.env`) kann sich nicht selbst löschen — API gibt `403` zurück, Frontend zeigt stattdessen informativen Hinweis

---

## Supabase-Integration: Schritt für Schritt

### Zwei Projekte, drei Umgebungen

| Umgebung | Supabase-Projekt | Zweck |
|---|---|---|
| Lokale Entwicklung | `schnappster-dev` | Entwicklung gegen echte Online-DB, kein Docker nötig |
| Integrationstests | `schnappster-dev` | Tests gegen dev-DB (RLS-Policies, Auth-Flows) |
| Unit-Tests | — | Supabase gemockt, läuft offline ohne Netzwerk |
| Produktion | `schnappster-prod` | Live-Betrieb |

Lokale Entwicklung nutzt die Online-dev-DB direkt — kein lokaler Docker-Stack, kein `npx supabase start`. Supabase-Features (RLS, Auth, E-Mail) funktionieren sofort.

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

### Schritt 5 — DB-Schema migrieren

**Einmalig — dev-Projekt:**

Im Supabase Dashboard → **SQL Editor** das neue Schema anlegen:

```sql
-- owner_id-Spalten hinzufügen (referenzieren Supabase auth.users)
ALTER TABLE ad_search ADD COLUMN owner_id UUID REFERENCES auth.users(id);
ALTER TABLE ad ADD COLUMN owner_id UUID REFERENCES auth.users(id);

-- UserSettings-Tabelle anlegen
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

Dasselbe SQL anschließend im prod-Projekt ausführen.

Zukünftige Schema-Änderungen: SQL-Datei in `migrations/` ablegen → dev testen → prod deployen.

---

### Schritt 6 — RLS Policies einrichten

Im SQL Editor (dev zuerst, dann prod):

```sql
-- RLS aktivieren
ALTER TABLE ad_search ENABLE ROW LEVEL SECURITY;
ALTER TABLE ad ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_settings ENABLE ROW LEVEL SECURITY;

-- Policies: jeder User sieht und verändert nur seine eigenen Daten
CREATE POLICY "users_own_searches" ON ad_search
    FOR ALL USING (auth.uid() = owner_id) WITH CHECK (auth.uid() = owner_id);

CREATE POLICY "users_own_ads" ON ad
    FOR ALL USING (auth.uid() = owner_id) WITH CHECK (auth.uid() = owner_id);

CREATE POLICY "users_own_settings" ON user_settings
    FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
```

Testen im SQL Editor mit `SET LOCAL role = authenticated; SET LOCAL request.jwt.claims = '{"sub": "<uuid>"}';` vor einer SELECT-Abfrage.

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

---

### Schritt 9 — Zwei DB-Sessions implementieren

**User-Context (`get_db_session`):** JWT-Claims werden als PostgreSQL-Session-Variable gesetzt → `auth.uid()` gibt die User-ID zurück → RLS filtert automatisch.

**Admin-Context (`get_admin_session`):** Verbindung mit `SUPABASE_SERVICE_ROLE_KEY` → RLS ist bypassed → `owner_id` in alle Queries und Inserts explizit schreiben.

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

Unit-Tests laufen vollständig offline — kein Netzwerk, keine Dev-DB:

```python
# tests/conftest.py
from fastapi.testclient import TestClient
from app.main import app
from app.core.auth import get_current_user

@pytest.fixture
def mock_user():
    return SimpleNamespace(id="test-uuid-1234", email="test@test.com",
                           app_metadata={"role": "user"})

@pytest.fixture(autouse=True)
def override_auth(mock_user):
    app.dependency_overrides[get_current_user] = lambda: mock_user
    yield
    app.dependency_overrides.clear()
```

Für DB-Assertions in Unit-Tests: lokales PostgreSQL oder `pytest-postgresql` (in-process PostgreSQL-Instanz). Für RLS-Tests: dev-DB via Integrationstest.

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

### Hosting-Empfehlung

**Empfehlung: Hetzner Cloud VPS**

| | Hetzner CX22 | DigitalOcean Basic | Railway | Render |
|---|---|---|---|---|
| **Preis** | ~€5/mo | ~$12/mo | ~$15–30/mo | ~$15–30/mo |
| **vCPU / RAM** | 2 / 4 GB | 1 / 1 GB | managed | managed |
| **Ops-Aufwand** | niedrig (Docker) | niedrig (Docker) | minimal | minimal |
| **Datenschutz** | DE-Server (DSGVO) | US-Server | US-Server | US-Server |
| **TLS** | via Caddy | via Caddy | automatisch | automatisch |

Hetzner CX22 (~€5/mo) bietet mehr als genug Ressourcen für Schnappster und hat deutsche Server (DSGVO-Vorteil). Der Ops-Aufwand mit Docker Compose ist gering.

Managed-Plattformen (Railway, Render, Fly.io) sind einfacher im Setup, kosten aber 3–6× mehr und haben US-Server. Sinnvoll wenn der Ops-Aufwand ein Problem ist.

### Deployment-Workflow

```bash
# Einmalig: Server einrichten
ssh root@<server-ip>
apt install docker.io docker-compose-plugin -y

# Repo klonen + starten
git clone https://github.com/pikktee/schnappster.git /opt/schnappster
cd /opt/schnappster
cp .env.example .env   # Credentials eintragen
docker compose up -d

# Update deployen
git pull && docker compose up -d --build
```

Für automatisches Deployment: GitHub Actions Workflow, der nach einem Push auf `main` per SSH `git pull && docker compose up -d --build` auf dem Server ausführt.

### Lokale Entwicklung (unverändert)

Lokal ändert sich nichts:
```bash
uv run start --skip-tests   # FastAPI auf :8000
cd web && npm run dev        # Next.js auf :3000 (proxied /api/* → :8000)
```

`npm run dev` ist bereits so konfiguriert dass API-Calls an `:8000` weitergeleitet werden — kein Caddy lokal nötig.

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

**Praktische Umsetzung:**
- API-Routen (User-Requests): nur RLS, kein WHERE nötig
- Hintergrundprozesse (Scraper): Service-Role + explizite Python-Logik
- Admin-Routen: Service-Role + `require_admin` Dependency

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
- `app/core/auth.py`: `get_current_user` + `require_admin` Dependencies implementieren (supabase-py, **Context7 nutzen**)
- `get_db_session()` (User-Context, RLS aktiv) und `get_admin_session()` (Service-Role) implementieren

**DB-Schema:**
- `owner_id UUID` auf `AdSearch` und `Ad` ergänzen (SQL Editor im dev-Projekt)
- `UserSettings`-Tabelle anlegen
- RLS aktivieren und Policies für alle User-Tabellen setzen
- Hintergrundjobs (ScraperService, AIService) auf `get_admin_session` + explizites `owner_id` umstellen

**Tests:**
- `conftest.py`: `get_current_user` Override für Unit-Tests, separates Admin-Fixture
- Bestehende Tests auf PostgreSQL-kompatible Fixtures umstellen
- `uv run pytest` muss grün sein

---

### Phase 2 — Frontend: Auth-Screens

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
- `DELETE /users/me` — Cascade-Delete: AdSearches → Ads → UserSettings → Supabase Auth User (Service-Role); Haupt-Admin geschützt (403)
- `POST /users/me/change-password` — via Supabase Auth API

---

### Phase 4 — Admin-Bereich

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

---

### Phase 6 — Payments (perspektivisch)

- Stripe-Subscriptions, Webhooks, Feature-Gates
- Wird erst geplant wenn Phase 5 abgeschlossen
