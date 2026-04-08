# 06 - Frontend-Auth und Session-Strategie

## Ziel

Robuste Session-Fuehrung zwischen Next.js Frontend und FastAPI API.

## Grundprinzip

- Frontend verwaltet Supabase-Session
- Backend validiert Access-Token pro Request

## Supabase JS Client

- Initialisierung mit `SUPABASE_URL` + `SUPABASE_ANON_KEY`
- `onAuthStateChange` fuer Login/Logout/Refresh
- Keine Service-Role Credentials im Browser

## API-Authentifizierung

- `Authorization: Bearer <access_token>` in API-Requests
- Bei gleicher Origin trotzdem konsistent Header senden

## Session-Speicher (Entscheidung)

- Option A: Standard Browser-Client (typisch localStorage) fuer schnellen Start
- Option B: httpOnly Cookies via SSR fuer haertere Security
- Gewaehlte Strategie dokumentieren, damit Middleware/Client konsistent bleiben

## Ablauf bei Session-Expiry

- Backend `401` -> Frontend Redirect nach `/login` bzw. Re-Auth Flow
- Optional preemptiver Refresh vor API-Calls

## Middleware-Hinweis

- Reines localStorage ist in Next-Middleware nicht direkt lesbar
- Fuer echtes serverseitiges Guarding ggf. SSR-Cookie-Strategie nutzen
