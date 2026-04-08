# 09 - Begruendungen und technische Entscheidungen

## Warum Supabase?

- Auth + DB + RLS aus einer Hand
- Schneller Start mit Managed Setup
- Dashboard fuer User-Management
- Gute Basis fuer spaetere Skalierung

## Warum RLS?

### Vorteile

- Datenisolierung auf DB-Ebene
- Schutz vor vergessenen `WHERE owner_id`-Filtern
- Einheitliche Zugriffssicherheit ueber verschiedene Pfade

### Nachteile / Kosten

- Policy-Debugging ist anspruchsvoller
- Background-Jobs benoetigen explizite Ownership-Logik

## Warum PostgreSQL statt SQLite?

- Concurrent Writes und Multi-User-Szenarien
- Keine typischen SQLite Write-Locks bei wachsendem Betrieb

## Warum Admin-HTTP Variante B?

- Kein Service-Role-SQL in normalen Admin-Routen
- Kleinerer Schadensradius bei Routing-/Codefehlern
- RLS bleibt auch fuer Admin-UI konsistent aktiv
