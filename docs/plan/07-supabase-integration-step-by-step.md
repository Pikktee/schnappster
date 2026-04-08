# 07 - Supabase Integration Schritt fuer Schritt

## Ziel

Migration von SQLite/Single-User auf Postgres/Supabase/Multi-Tenancy.

Hinweis: Externe/Portal-Schritte (Projektanlage, Provider-Konfiguration, Secrets-Verwaltung)
sind absichtlich ausgelagert nach `90-manual-supabase-and-external-setup.md`.

## 1) Abhaengigkeiten und Backend-Basis

- `uv add supabase asyncpg`
- DB-Engine auf `DATABASE_URL` (Postgres) umstellen
- SQLite-spezifischen Engine-Pfad entfernen

## 2) Schema (Greenfield)

- `ad_search` + `ad` um `owner_id` erweitern
- `user_settings` anlegen
- `app_settings` anlegen (admin-only Zugriff)
- SQLModel und DB-Schema 1:1 synchron halten
- Zukuenftige Aenderungen via `supabase/migrations/`

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

- `get_db_session()`: User-JWT + RLS fuer alle HTTP-Routen
- `get_admin_session()`: nur Background-Jobs
- JWT-Claims pro Request in Postgres-Session setzen (`request.jwt.claims` etc.)

## 6) Tests

- Auth in pytest mocken (`dependency_overrides`)
- SQL-nahe Tests gegen echte PostgreSQL-Instanz
- Optional RLS-Integration via lokalem Supabase oder isoliertem Projekt
