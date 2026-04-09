# Supabase Admin-Rolle initialisieren (Dev)

## Zweck

Diese Anleitung beschreibt, wie im Supabase-Projekt der erste Admin gesetzt wird,
auch wenn anfangs noch keine App-UI oder kein OAuth-Login verfuegbar ist.

## Warum "No rows returned"?

Wenn bei `SELECT` oder `UPDATE` auf `auth.users` keine Zeilen zurueckkommen, gibt es meist zwei Ursachen:

- Es existiert noch kein User in `auth.users`.
- Die abgefragte E-Mail passt nicht exakt zu einem vorhandenen User.

## Schritt 1: Vorhandene User pruefen

Im Supabase SQL Editor:

```sql
select email
from auth.users
limit 20;
```

Interpretation:

- Leere Ergebnismenge: Es gibt noch keine Auth-User.
- Treffer vorhanden: Fuer weitere Queries exakt eine vorhandene E-Mail verwenden.

## Schritt 2: Falls noetig User anlegen

Falls noch kein User existiert:

- `Authentication -> Users -> Add user`
- Test-User mit deiner E-Mail anlegen (z. B. fuer Dev)

## Schritt 3: Admin-Rolle setzen

```sql
update auth.users
set raw_app_meta_data = coalesce(raw_app_meta_data, '{}'::jsonb) || '{"role":"admin"}'::jsonb
where email = 'deine@echte-mail.tld';
```

## Schritt 4: Ergebnis verifizieren

```sql
select
  email,
  raw_app_meta_data
from auth.users
where email = 'deine@echte-mail.tld';
```

Erwartung: `raw_app_meta_data` enthaelt `"role": "admin"`.

## Optional: Admin-Rolle wieder entfernen

```sql
update auth.users
set raw_app_meta_data = coalesce(raw_app_meta_data, '{}'::jsonb) - 'role'
where email = 'deine@echte-mail.tld';
```

## Hinweise

- `DEINE_EMAIL` ist nur ein Platzhalter und muss ersetzt werden.
- `raw_app_meta_data` ist der uebliche Ort fuer Rollen-Claims in Supabase Auth.
- JWT-Claim-Pruefung kann spaeter erfolgen, sobald Login/UI integriert ist.
