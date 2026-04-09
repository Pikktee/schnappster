# 10 - Phasenplan der Umsetzung

## Phase 1 - Backend: Auth und Multi-Tenancy

1. Manuelle Vorarbeiten aus `90-manual-supabase-and-external-setup.md` abschliessen
2. Backend-Migration auf Postgres/Supabase (Static Export bleibt vorerst funktionsfaehig)
3. RLS-Policies und Session-Kontexte
4. Jobs auf Service-Role + `owner_id` umstellen
5. Tests auf Postgres-kompatiblen Stand bringen (Alembic Baseline)
6. Deployment-Umbau: API/Frontend Trennung auf Railway/Vercel, Domains + CORS-Konfiguration (erst wenn Backend stabil auf Postgres laeuft)

## Phase 2 - Frontend: Auth-Screens

- Oeffentliche Seiten: `/impressum`, `/datenschutz`
- `(auth)` Route-Group aufbauen
- Login/Register/Forgot/Reset implementieren
- Supabase JS Session-State integrieren

## Phase 3 - Account-Management

- User-Settings Seite erweitern
- Profil, Passwortfluss, Benachrichtigungsoptionen
- Danger Zone fuer Konto-Loeschung
- User-Endpunkte fuer Profil/Settings/Loeschung

## Phase 4 - Admin-Bereich

- Bestehende Routen mit `require_admin` absichern
- Admin-Endpunkte fuer manuelle Trigger + Stats
- Sidebar/Admin-Dashboard fuer Admins
- Logs als systemweite, admin-only API-Ressourcen finalisieren (kein User-Delete-Cleanup)

## Phase 5 - Betrieb

- Telegram/E-Mail Benachrichtigungen
- Rate-Limiting, Monitoring
- CORS- und Datenschutz-Betriebsprozesse dauerhaft pflegen und regelmaessig pruefen
- Manuelle Deployment-/Ops-Schritte aus `91-manual-deployment-and-operations.md` anwenden

## Phase 6 - Payments (spaeter)

- Stripe Subscriptions/Webhooks
- Feature-Gates ueber Plan/Entitlements
- Keine Rollenexplosion fuer Paid-Tiers
