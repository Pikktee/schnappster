# Subprozessoren-Liste (Schnappster)

Stand: 2026-04-08
Status DPA Supabase: beantragt (Bearbeitung kann bis zu 24h dauern)

## Zweck

Diese Liste dokumentiert externe Dienstleister (Subprozessoren), die personenbezogene Daten
im Rahmen von Schnappster verarbeiten oder verarbeiten koennen.

## Subprozessoren (aktuell / geplant)

| Dienst | Zweck | Datenkategorien | Region | Vertrag / DPA | Status |
| --- | --- | --- | --- | --- | --- |
| Supabase | Datenbank, Authentifizierung, ggf. Storage | Accountdaten (E-Mail, User-ID), App-Daten, Metadaten, Logs | Abhaengig vom gewaehlten Projekt-Region-Setup | DPA beantragt | Aktiv (Dev) |
| Hosting-Provider (noch offen) | Betrieb von Backend/Frontend in Production | Betriebsdaten, IP/Request-Logs, ggf. Sessiondaten | Offen | Offen | Geplant |
| Monitoring/Logging (noch offen) | Fehleranalyse, Performance, Betriebsmonitoring | Fehlerlogs, technische Metadaten, ggf. IP-Adressen | Offen | Offen | Optional / Geplant |
| E-Mail-Provider (noch offen) | Versand transaktionaler E-Mails (z. B. Login/Info) | E-Mail-Adresse, Versand-Metadaten | Offen | Offen | Optional / Geplant |

## Hinweise zur Pflege

- Diese Datei bei jeder Tool-Einfuehrung aktualisieren.
- Fuer jeden neuen Dienst mindestens Zweck, Datenkategorien und Vertragsstatus dokumentieren.
- Vor Produktivstart offene Felder (`Offen`) verbindlich ausfuellen.

## Offene To-dos vor Production

- Hosting-Provider festlegen und eintragen
- Monitoring/Logging-Stack festlegen und eintragen
- E-Mail-Provider festlegen (falls benoetigt) und eintragen
- DPA-Status Supabase von `beantragt` auf `abgeschlossen` aktualisieren
