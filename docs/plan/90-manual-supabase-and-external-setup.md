# 90 - Manuell: Supabase und externe Setups

## Zweck

Diese Schritte werden bewusst **manuell** durchgefuehrt (Dashboard, Provider-Portale, Secrets).
Nicht als KI-Agentenplan verwenden.

## Supabase Projekte

- Projekt `schnappster-dev` anlegen
- Projekt `schnappster-prod` anlegen
- Notieren: Project URL, Publishable key, Secret key, Database URL (Direct connection string)
- Optional zusaetzlich notieren: Pooler connection string (fuer serverless/kurzlebige Verbindungen)

## OAuth Provider

- Google OAuth App anlegen und Callback-URL in Supabase eintragen
- Facebook App anlegen und Callback-URL in Supabase eintragen
- Site URL + Redirect URLs fuer dev/prod setzen

## Rolleninitialisierung

- Ersten Admin in Supabase SQL Editor setzen (`raw_app_meta_data.role = admin`)
- Admin-Claim im JWT pruefen

## Rechtliches / externe Verwaltung

- DPA/AVV mit Supabase abschliessen und dokumentieren
- Subprozessoren (Mail, Monitoring, Hosting) dokumentieren

## Secrets Management

- Lokal eine gemeinsame Root-`.env` pflegen (nicht committen)
- `NEXT_PUBLIC_*` Werte in derselben Root-`.env` mitpflegen
- Produktions-Secrets im Host/Secret-Manager setzen
- `SUPABASE_SECRET_KEY` nie im Frontend verwenden
