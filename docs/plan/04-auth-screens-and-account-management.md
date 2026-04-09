# 04 - Auth-Screens und Account-Management

## Ziel

Vollstaendige Login-/Account-UX fuer Multi-User.

## Auth-Screens

- Route-Group `(auth)` ohne Sidebar
- Design: `gradient-subtle`, Amber-Akzent, Lexend, Card-zentriert
- Sprache: Deutsch
- Fehler via `toast.error`, Erfolg mit direkter Weiterleitung

## Routen

- `/login`
- `/register`
- `/forgot-password`
- `/reset-password`

## Login/Register Inhalte

- Social Login: Google, Facebook
- E-Mail/Passwort-Formulare
- Links zwischen Login/Register/Forgot Password

## Passwort-Flows

- Forgot Password: neutrale Antwort (keine User-Enumeration)
- Reset Password: Supabase Token aus URL verwenden
- Passwort aendern in Settings nur fuer E-Mail/Passwort-User

## Konto loeschen (Danger Zone)

- Destruktiver Bereich mit `AlertDialog`
- Bestaetigung erst nach Eingabe `loeschen`
- App-Daten werden im User-Context explizit ueber `owner_id` geloescht:
  `user_settings`, `ad_search`
  (wobei `ad` via `ON DELETE CASCADE` an `ad_search` haengt)
- Logs bleiben systemweit/admin-only und sind nicht Teil des User-Delete-Flows
- Kein DB-Design voraussetzen, das per FK direkt an `auth.users` kaskadiert
- Danach Auth-User via Supabase Admin API loeschen
- Endpoint-Verhalten idempotent halten (wiederholter Aufruf bleibt sicher)
- Falls Auth-Delete fehlschlaegt: `deletion_pending` markieren und Retry erlauben
- Primaeren Admin vor Selbstloeschung schuetzen (`403`)

## Backend-Endpunkte (Account)

- `GET/PATCH /users/me`
- `GET/PATCH /users/me/settings`
- `POST /users/me/change-password`
- `DELETE /users/me`
