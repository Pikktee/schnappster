# 07 - Supabase Integration Schritt fuer Schritt

## Ziel

Migration von SQLite/Single-User auf Postgres/Supabase/Multi-Tenancy.

Hinweis: Externe/Portal-Schritte (Projektanlage, Provider-Konfiguration, Secrets-Verwaltung)
sind absichtlich ausgelagert nach `90-manual-supabase-and-external-setup.md`.

## 1) Abhaengigkeiten und Backend-Basis

- `uv add psycopg[binary]` (sync Driver fuer PostgreSQL, kein async-Umbau noetig)
- `supabase`-Paket nur falls Admin-API benoetigt (User loeschen etc.), sonst reicht SQLAlchemy + psycopg
- DB-Engine auf `DATABASE_URL` (Postgres) umstellen (`postgresql+psycopg://...`)
- SQLite-spezifischen Engine-Pfad und PRAGMA-Logik entfernen

## 2) Schema (Greenfield)

- Greenfield: App startet mit leerem Postgres, kein Datenimport aus SQLite
- `ad_search` + `ad` um `owner_id` erweitern
- `user_settings` anlegen
- `app_settings` anlegen (admin-only Zugriff)
- SQLModel und DB-Schema 1:1 synchron halten
- Initiales Schema via Alembic-Baseline-Migration erstellen
- Zukuenftige Schema-Aenderungen via **Alembic** (Auto-Generate aus SQLModel-Definitionen)
- `uv run dbreset` bleibt nur fuer lokale Entwicklung; Produktion immer ueber Alembic
- RLS-Policies als separate SQL-Migrationen in Alembic verwalten

## 3) RLS und Policies

- RLS auf allen Multi-Tenant-Tabellen aktivieren
- Owner-Policies fuer `ad_search`, `ad`, `user_settings`
- Admin-Policy fuer `app_settings` via `app_metadata.role = admin`
- Policy-Tests mit passenden JWT-Claims (inkl. `app_metadata`)

## 4) Auth und Rollen

- `get_current_user`
- `require_admin`
- Admin-Rolle in `raw_app_meta_data` setzen
- Konsistenz zwischen Python-Check (`user.app_metadata`) und SQL-Policy (`auth.jwt()`)

## 5) Session-Kontexte

### Ueberblick

- `get_db_session()`: User-JWT + RLS fuer alle HTTP-Routen
- `get_admin_session()`: nur Background-Jobs (dedizierter Admin-Kontext, nie in normalen HTTP-Routen)

### Ablauf: JWT-Claims an PostgreSQL uebergeben

```
Request mit Bearer Token
    ↓
get_current_user()          — Token validieren, Claims extrahieren
    ↓
get_db_session(user)        — DB-Session oeffnen, Claims setzen
    ↓
SET LOCAL request.jwt.claims = '{"sub":"<user-id>", ...}'
SET LOCAL role = 'authenticated'
    ↓
Query ausfuehren            — RLS-Policies lesen request.jwt.claims
    ↓
Transaction commit/rollback — SET LOCAL wird automatisch zurueckgesetzt
```

### Pseudocode `get_db_session()`

```python
def get_db_session(current_user = Depends(get_current_user)):
    with Session(engine) as session:
        # Claims als Postgres-Session-Variable setzen
        # SET LOCAL gilt nur innerhalb dieser Transaction
        claims = json.dumps({
            "sub": str(current_user.id),
            "role": "authenticated",
            "app_metadata": current_user.app_metadata,
        })
        session.execute(text("SET LOCAL request.jwt.claims = :claims"), {"claims": claims})
        session.execute(text("SET LOCAL role = 'authenticated'"))
        yield session
```

### Pseudocode `get_admin_session()`

```python
def get_admin_session():
    """Nur fuer Background-Jobs: dedizierter Admin-Kontext, kein User-JWT."""
    with Session(engine) as session:
        # Rechte kommen aus der tatsaechlichen DB-Role/Connection-Strategie,
        # nicht aus einer missverstaendlichen Annahme ueber SET LOCAL role.
        yield session
```

### RLS-Policy liest die Claims

```sql
-- Beispiel: Owner-Policy fuer ad_search
CREATE POLICY owner_access ON ad_search
    USING (owner_id = (current_setting('request.jwt.claims', true)::json->>'sub')::uuid);
```

### Wichtig

- `SET LOCAL` gilt nur innerhalb der aktuellen Transaction — kein Leak zwischen Requests
- Normale HTTP-Routen verwenden niemals `get_admin_session()`
- Background-Jobs nutzen einen expliziten Admin-Kontext mit klar dokumentierter Rechtevergabe
- `owner_id` wird bei INSERT explizit aus den Claims gesetzt (nicht von RLS)
- Kein Sicherheitsdesign auf der Annahme aufbauen, dass `SET LOCAL role = 'service_role'`
  automatisch RLS korrekt umgeht

## 6) API-Routen-Uebersicht (Ist → Soll)

### Bestehende Routen — Aenderungen

Alle bestehenden Routen bekommen `get_current_user` als Dependency.
RLS filtert automatisch nach `owner_id` — kein manuelles `WHERE owner_id` noetig.

| Route | Methode(n) | Auth | Aenderung |
|-------|-----------|------|-----------|
| `/api/ads` | GET | user | RLS filtert auf eigene Ads |
| `/api/ads/{id}` | GET | user | RLS filtert auf eigene Ads |
| `/api/adsearches` | GET, POST | user | POST setzt `owner_id` aus JWT |
| `/api/adsearches/{id}` | GET, PATCH, DELETE | user | RLS filtert auf eigene Searches |
| `/api/adsearches/{id}/scrape` | POST | user | Triggert Scrape nur fuer eigene Search |
| `/api/version` | GET | public | Keine Aenderung |

### Bestehende Routen — Aufspaltung Settings

`/api/settings` wird aufgeteilt:

| Route | Methode(n) | Auth | Beschreibung |
|-------|-----------|------|-------------|
| `/api/settings` | GET, PUT | admin | Globale AppSettings (ehemals `/api/settings/{key}`) |
| `/api/settings/telegram-configured` | GET | admin | Telegram-Bot-Status |

### Neue Routen — User/Account (Phase 2-3)

| Route | Methode(n) | Auth | Beschreibung |
|-------|-----------|------|-------------|
| `/api/users/me` | GET, PATCH | user | Eigenes Profil (Name, Avatar-URL) |
| `/api/users/me/settings` | GET, PATCH | user | Persoenliche Einstellungen (Benachrichtigungen etc.) |
| `/api/users/me/change-password` | POST | user | Nur fuer E-Mail/Passwort-User |
| `/api/users/me` | DELETE | user | Konto loeschen (Kaskade + Supabase Admin API) |

### Bestehende Routen — Logs (werden Admin-only)

| Route | Methode(n) | Auth | Beschreibung |
|-------|-----------|------|-------------|
| `/api/scraperuns` | GET, DELETE | admin | Scrape-Logs (systemweit) |
| `/api/aianalysislogs` | GET, DELETE | admin | AI-Analyse-Logs (systemweit) |
| `/api/errorlogs` | GET, DELETE | admin | Fehler-Logs (systemweit) |

### Neue Routen — Admin (Phase 4)

| Route | Methode(n) | Auth | Beschreibung |
|-------|-----------|------|-------------|
| `/api/admin/scrape` | POST | admin | Manueller Scrape-Trigger (systemweit) |
| `/api/admin/analyze` | POST | admin | Manuelle AI-Analyse (systemweit) |

User-Management erfolgt initial ueber das Supabase Dashboard (kein eigener Endpoint).

## 7) Tests (nach Prioritaet)

### Muss: Unit Tests (Business-Logik, Parser, Filter)

- Bestehende Tests bleiben und werden angepasst
- Auth wird gemockt (`dependency_overrides` fuer `get_current_user`)
- Keine echte Postgres noetig — gemockte DB/Services reichen
- `uv run pytest` bleibt schnell und laeuft ohne externe Abhaengigkeiten

### Muss: Security-Invariants (leichtgewichtig, aber verpflichtend)

- Test/Check 1: User-HTTP-Route kann keine systemweiten Admin-Operationen ausfuehren
- Test/Check 2: Background-Job mit Admin-Kontext kann benoetigte systemweite Operation ausfuehren
- Test/Check 3: `get_admin_session()` wird nicht in normalen HTTP-Routen verwendet

### Sollte (nach MVP): DB-Tests gegen Postgres

- Testen, ob SQLModel-Queries und Alembic-Migrationen korrekt funktionieren
- Benoetigt Postgres-Docker-Container in Test-Config
- Nicht Tag-1-kritisch, aber sinnvoll sobald der Betrieb stabil laeuft

### Kann (manuell reicht): RLS-Integrationstests

- Pruefen, ob User A die Daten von User B nicht sieht
- RLS-Policies sind einfaches SQL und aendern sich selten
- Manuelles Testen mit zwei Test-Usern reicht aus
- Automatisierte RLS-Tests nur bei haeufigen Policy-Aenderungen sinnvoll

## 8) Lokale Entwicklung

- **Entwicklung:** Remote Supabase Dev-Projekt (`schnappster-dev`) — `.env` auf Dev-Projekt zeigen
- **Unit Tests:** Gemockte Auth, keine externe Abhaengigkeit
- Supabase CLI lokal ist nicht noetig (Solo-Dev, Remote-Projekt reicht)
