# 05 - Impressum, Datenschutz und DSGVO

## Ziel

Rechtlich notwendige oeffentliche Seiten und Datenschutz-Grundlagen fuer SaaS-Betrieb.

## Impressum

- Oeffentliche Route `/impressum`
- Statische Seite (kein API-Call)
- Inhalt gemaess §5 TMG
- Link in Sidebar-Footer und Auth-Screens
- Route ausserhalb auth-erzwungenem Layout platzieren

## Datenschutz

- Oeffentliche Route `/datenschutz`
- Statische Seite
- Inhalt: Verantwortlicher, Zweck, Rechtsgrundlagen, Subprozessoren, Betroffenenrechte
- Konto-Loeschung und Datenverarbeitung (inkl. Telegram-Chat-ID) dokumentieren

## Middleware-Regeln

- `/impressum` und `/datenschutz` von Auth-Redirect ausnehmen

## DSGVO-Betrieb

- DPA/AVV mit Supabase abschliessen und pflegen
- Weitere Dienstleister (Mail, Monitoring, Hosting) dokumentieren
- Bei neuen Features Datenschutzerklaerung nachziehen
