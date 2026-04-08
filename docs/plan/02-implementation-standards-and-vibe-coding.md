# 02 - Implementierungsstandards und Vibe-Coding

## Ziel

Qualitaet und Konsistenz waehrend der Migration sichern.

## Vibe-Coding Hinweise

### Funktioniert gut

- FastAPI, SQLModel, Next.js, shadcn/ui
- SQL-basierte RLS-Policies
- pytest + FastAPI TestClient

### Kritische Stolperstellen

- `supabase-py` API gegen aktuelle Doku/Context7 pruefen
- RLS vs. Service-Role immer explizit kennzeichnen
- APScheduler-Jobs haben keinen User-Context; `owner_id` in Job-Code explizit setzen

## Code-Stil

- Sprechende Namen, keine kryptischen Abkuerzungen
- Funktionen moeglichst kurz (~20 Zeilen), komplexe Logik auslagern
- Early Return statt tiefer Verschachtelung
- Keine auskommentierten Codebloecke
- Keine Magic Numbers, stattdessen benannte Konstanten
- Kommentare erklaeren Warum, nicht Was

## Python/FastAPI Konventionen

- Vollstaendige Type Hints, `Any` nur begruendet
- `# type: ignore` nur wenn unvermeidbar
- Duenne Routen: validieren -> Service -> Response
- Services via `Depends()`, nicht direkt instanziieren
- Statuscodes explizit setzen (`201`, `204`, ...)
- Request/Response immer via Pydantic/SQLModel-Schemas
- `HTTPException` mit klarem `detail`
- Async fuer IO, Sync fuer CPU-lastige reine Logik

## Testing-Konventionen

- Verhalten testen, nicht interne Implementierungsdetails
- Neue Services/Filter mit Unit-Tests absichern
- `uv run pytest` vor jedem Merge gruen
- Supabase-Auth in pytest mocken
- SQL-nahe Tests gegen echte PostgreSQL-Instanz

## Agenten-Workflow nach Umsetzung

- Stabile Regeln spaeter in `AGENTS.md` uebernehmen.
- Diese Plan-Dateien bleiben Planungs-/Migrationsartefakte.
