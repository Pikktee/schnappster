# 01 - Foundation: Architektur und Grundprinzipien

## Ziel

Klarer technischer Rahmen, bevor Implementierungsdetails starten.

## Tech-Stack (neu)

- Datenbank: PostgreSQL (Supabase)
- Auth: Supabase Auth (Google/Facebook, E-Mail/Passwort)
- Datenisolierung: PostgreSQL RLS
- Rollen: `user`, `admin`

## Tech-Stack (bleibt)

- Backend: FastAPI + SQLModel
- Scraping: curl-cffi + BeautifulSoup
- AI: OpenAI-kompatible API
- Jobs: APScheduler
- Frontend: Next.js + React + Tailwind + shadcn/ui

## Verbindliche Architekturentscheidung: Admin-HTTP = Variante B

- Alle HTTP-Routen (User + Admin) verwenden `get_db_session()` mit User-JWT.
- RLS bleibt in HTTP-Routen immer aktiv.
- Admin-Rechte werden durch `require_admin` plus RLS-Policies vergeben.
- `get_admin_session()` (Service Role) ist nur fuer Background-Jobs.
- `DELETE /users/me`: erst App-Daten im User-Context ueber `owner_id` loeschen
  (`user_settings`, `ad_search` mit `ad`-Kaskade), danach Auth-User
  via Supabase Admin API loeschen.
- Variante A (Service-Role-SQL fuer normale Admin-HTTP-Routen) wird nicht verwendet.

## Future-Proofing fuer Payments

- Bezahlte Stufen nicht als Rollen modellieren.
- Rollen bleiben fuer Berechtigungen (`user`/`admin`).
- Paid-Tiers spaeter als Plan/Entitlements (z. B. `free`, `premium`) ergaenzen.
