# Google OAuth Setup (Dev)

## Zweck

Diese Anleitung beschreibt die Einrichtung von Google OAuth fuer `schnappster-dev` mit Supabase.
Production ist bewusst ausgeklammert und kann spaeter analog eingerichtet werden.

## Voraussetzungen

- Supabase Projekt `schnappster-dev` existiert
- Google Cloud Projekt existiert
- Lokale App laeuft (z. B. Frontend auf `http://localhost:3000`)

## 1) Supabase vorbereiten

1. In Supabase zu `Authentication -> Sign In / Providers` gehen.
2. `Google` Provider oeffnen.
3. Die Supabase Callback URL notieren (typisch: `https://<project-ref>.supabase.co/auth/v1/callback`).
4. In `Authentication -> URL Configuration` setzen:
   - `Site URL`: `http://localhost:3000`
   - `Redirect URLs`: mindestens `http://localhost:3000/**`

## 2) Google OAuth App anlegen

1. In der Google Cloud Console `APIs & Services` oeffnen.
2. `OAuth consent screen` konfigurieren (App-Name, Support-Email, Developer-Email).
3. Bei Bedarf Test-User hinterlegen (solange die App im Testmodus ist).
4. Unter `Credentials -> Create Credentials -> OAuth client ID`:
   - Application Type: `Web application`
   - `Authorized redirect URIs`: Supabase Callback URL eintragen
5. `Client ID` und `Client Secret` kopieren.

## 3) Google in Supabase aktivieren

1. Zurueck in Supabase `Authentication -> Sign In / Providers -> Google`.
2. `Client ID` und `Client Secret` eintragen.
3. Provider aktivieren und speichern.

## 4) End-to-End Test (Dev)

1. App lokal starten (Frontend + Backend im Dev-Modus).
2. In der App den Google-Login ausloesen.
3. Im Browser pruefen:
   - Weiterleitung zu Google funktioniert.
   - Nach Login Rueckleitung auf `localhost` erfolgt.
4. In Supabase `Authentication -> Users` pruefen:
   - Neuer User wurde angelegt oder bestehender User aktualisiert.
   - Provider ist `google`.
5. In der App pruefen:
   - Session ist aktiv.
   - Geschuetzte Seiten sind erreichbar.

## 5) Fehlercheckliste

- Redirect URL stimmt nicht exakt (haeufigster Fehler)
- Falsches Supabase Projekt (dev/prod verwechselt)
- Google App noch im Testmodus ohne passenden Test-User
- In Supabase Site URL/Redirect URLs unvollstaendig
- Falsche Client ID/Secret in Supabase gespeichert

## Notizen fuer spaeter (Prod)

- Eigene Google OAuth Client-Konfiguration fuer Production erstellen
- Eigene Site URL und Redirect URLs fuer Production setzen
- Dev- und Prod-Secrets strikt getrennt halten
