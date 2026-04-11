# SQL-Migrationen (MVP)

Die Migrationen werden manuell und in Reihenfolge ausgefuehrt:

1. `001_init.sql`
2. `002_rls_policies.sql`

Beispiel (psql):

```bash
psql "$DATABASE_URL" -f docs/db/migrations/001_init.sql
psql "$DATABASE_URL" -f docs/db/migrations/002_rls_policies.sql
```

Hinweis: `uv run dbreset` bleibt ein lokales Dev-Werkzeug; Produktivumgebungen sollen diese SQL-Migrationen verwenden.
