# Schnappster SaaS Roadmap (Uebersicht)

## Zielbild

Schnappster wird von Single-User (SQLite, keine Auth) zu einer Multi-User-SaaS mit:

- Supabase Auth (Google/Facebook, E-Mail/Passwort)
- PostgreSQL + RLS-basierter Datenisolierung
- Admin-Funktionen mit Variante B (Admin-HTTP ueber User-JWT + RLS, kein Service-Role-SQL in normalen Admin-Routen)
- optionalen Benachrichtigungskanaelen (Telegram, E-Mail, Web Push)
- spaeterer Erweiterbarkeit Richtung Payments/Entitlements

## Reihenfolge der KI-Agenten-Teilplaene

1. `01-foundation-architecture-and-principles.md`
2. `02-implementation-standards-and-vibe-coding.md`
3. `03-user-profile-and-notifications.md`
4. `04-auth-screens-and-account-management.md`
5. `05-imprint-and-privacy-gdpr.md`
6. `06-frontend-auth-session-strategy.md`
7. `07-supabase-integration-step-by-step.md`
8. `08-deployment-and-infrastructure.md`
9. `09-rationale-and-technical-decisions.md`
10. `10-phased-execution-plan.md`

## Manuelle Checklisten (ohne KI-Agent)

- `90-manual-supabase-and-external-setup.md`
- `91-manual-deployment-and-operations.md`

## Wichtige Leitplanken

- `01` bis `10` sind KI-Agenten-Umsetzungsplaene (Code, Tests, Refactoring).
- `90` und `91` sind manuelle Aufgaben (Dashboards, Provider-Setup, Server-Ops).
- `AGENTS.md` bleibt bis zur Umsetzung auf Ist-Zustand; neue Regeln erst nach Implementierung uebernehmen.
- Fuer spaetere Premium-Modelle: Rolle (`user`/`admin`) getrennt von Plan/Entitlements (`free`/`premium`) halten.
