# Dev Auth Checkliste (Supabase + Google OAuth)

## Ziel

Schnelle Uebersicht, ob die Auth-Basis fuer Development korrekt eingerichtet ist.

## Checkliste

- [ ] Supabase Projekt `schnappster-dev` ist angelegt
- [ ] Project URL ist notiert
- [ ] Publishable key ist notiert
- [ ] Secret key ist notiert (nur serverseitig verwenden)
- [ ] Database URL (Direct connection string) ist notiert
- [ ] Google OAuth App in Google Cloud ist erstellt
- [ ] Supabase Callback URL ist in Google als Redirect URI hinterlegt
- [ ] Google Client ID/Secret sind in Supabase Provider-Einstellungen gesetzt
- [ ] `Site URL` und `Redirect URLs` fuer localhost sind gesetzt
- [ ] Mindestens ein User existiert in `auth.users`
- [ ] Erster Admin ist gesetzt (`raw_app_meta_data.role = admin`)

## Aktuell bewusst spaeter

- End-to-End Login-Test in der App-UI (wenn UI/Flow fertig ist)
- Production OAuth Setup (eigene URL/Redirects/Secrets)
- Facebook OAuth (optional, aktuell aus Scope)
