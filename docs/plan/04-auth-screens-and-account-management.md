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
- App-Daten kaskadieren via `ON DELETE CASCADE` in der DB:
  `user → user_settings, ad_search → ad, logs_scraperun, logs_aianalysis, logs_error`
- Danach Auth-User via Supabase Admin API loeschen
- Primaeren Admin vor Selbstloeschung schuetzen (`403`)

## Backend-Endpunkte (Account)

- `GET/PATCH /users/me`
- `GET/PATCH /users/me/settings`
- `POST /users/me/change-password`
- `DELETE /users/me`
