# 06 - Frontend-Auth und Session-Strategie

## Ziel

Robuste Session-Fuehrung zwischen Next.js Frontend und FastAPI API.

## Grundprinzip

- Frontend verwaltet Supabase-Session
- Backend validiert Access-Token pro Request
- Security-Boundary ist die API (401 ohne gueltiges Token), nicht das Frontend

## Entscheidung: localStorage + Bearer-Token (clientseitig)

- Supabase JS Client speichert Session im localStorage (Standardverhalten)
- API-Requests senden `Authorization: Bearer <access_token>`
- Kein SSR, kein Cookie-basiertes Session-Management
- Static Export bleibt moeglich

### Begruendung

- Einfachste Integration mit Supabase JS Client
- Kein serverseitiges Session-Handling noetig
- API ist der Security-Boundary — das Frontend ist eine leere Shell ohne Daten
- Fuer ein Dashboard ausreichend; sensible Daten werden nie ohne gueltiges Token ausgeliefert

## Supabase JS Client

- Initialisierung mit `SUPABASE_URL` + `SUPABASE_ANON_KEY`
- `onAuthStateChange` fuer Login/Logout/Refresh
- Keine Service-Role Credentials im Browser

## Route-Guarding (clientseitig)

- Auth-Provider im Root-Layout prueft Supabase-Session beim App-Start
- Globaler Loading-State (Spinner) bis Session-Status bekannt
- Geschuetzte Seiten: kein Token -> Redirect nach `/login`
- Oeffentliche Seiten (`/login`, `/register`, `/impressum`, `/datenschutz`): kein Guard
- Kein serverseitiges Guarding via Next.js Middleware

## API-Authentifizierung

- `Authorization: Bearer <access_token>` in allen API-Requests
- Bei gleicher Origin (hinter Caddy) trotzdem konsistent Header senden

## Ablauf bei Session-Expiry

- Backend `401` -> Frontend Redirect nach `/login`
- Supabase JS Client refresht Tokens automatisch via `onAuthStateChange`
- Optional: preemptiver Token-Check vor API-Calls
