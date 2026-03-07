# Schnappster — Architektur-Review & Verbesserungsplan

Erstellt am: 2026-03-07
Perspektive: Senior Software Architect

## Gesamtbewertung

Das Projekt hat eine **solide Grundarchitektur** (8/10): saubere Layer-Trennung, keine zirkulaeren Abhaengigkeiten, korrekte Session-Verwaltung. Es gibt jedoch **kritische Sicherheitsluecken** und Potenzial fuer bessere Code-Organisation.

---

## Phase 1 — Kritische Sicherheitsluecken (P0, sofort)

### 1.1 API-Key im Repository exponiert
- **Datei:** `.env`
- `.env` enthaelt einen echten `OPENROUTER_API_KEY`
- **Aktion:**
  - Key sofort bei OpenRouter revoken
  - `.env` aus Git-History entfernen (`git filter-repo`)
  - `.env` in `.gitignore` sicherstellen

### 1.2 Offene CORS-Konfiguration
- **Datei:** `app/main.py:28-34`
- `allow_origins=["*"]` + `allow_credentials=True` — widerspricht sich und erlaubt jeder Website API-Zugriff
- **Aktion:** Origins auf konkrete Domain(s) einschraenken oder `allow_credentials` entfernen

### 1.3 Keine Authentifizierung
- **Dateien:** Alle Endpoints in `app/api/`
- Alle API-Endpoints sind voellig ungeschuetzt — jeder mit Netzwerkzugriff kann Daten lesen, Suchen loeschen, Settings aendern, AI-Analyse triggern
- **Aktion:** Mindestens API-Key-Auth oder Basic-Auth einfuehren; fuer Produktivbetrieb JWT oder Session-basiert

---

## Phase 2 — Sicherheitshaertung (P1, diese Woche)

### 2.1 SSRF-Schutz bei URL-Eingabe
- **Datei:** `app/api/adsearch.py:38`
- `url` Feld akzeptiert beliebige URLs ohne Validierung
- Scraper fetcht diese blind — SSRF moeglich (interne Netzwerke scannen)
- **Aktion:** URL-Validierung auf `https://www.kleinanzeigen.de/*` einschraenken, private IPs blocken

### 2.2 Unvalidierte Image-URLs
- **Datei:** `app/services/ai.py:180-205`
- Image-URLs aus gescraptem HTML werden ohne Pruefung geladen
- **Aktion:** URLs auf bekannte Kleinanzeigen-Domains validieren, Groessenlimit setzen

### 2.3 Security Headers hinzufuegen
- **Datei:** `app/main.py`
- Kein CSP, X-Frame-Options, HSTS, X-Content-Type-Options
- **Aktion:** FastAPI-Middleware fuer Security Headers, `TrustedHostMiddleware`

### 2.4 Input-Validierung verschaerfen
- **Dateien:** `app/models/adsearch.py`, `app/services/settings.py`
- `prompt_addition`, `blacklist_keywords` ohne Laengenlimit — Prompt-Injection-Risiko fuer AI
- **Aktion:** `max_length` Validatoren, Sanitisierung fuer AI-Prompt-Felder

### 2.5 Path-Traversal Schutz
- **Datei:** `app/main.py:44-108`
- File-Serving fuer Frontend-Detail-Pages validiert `section` Parameter nicht gegen Whitelist
- **Aktion:** `section` gegen `["searches", "ads"]` validieren, `Path.resolve().relative_to()` nutzen

### 2.6 Informationsleck Telegram-Endpoint
- **Datei:** `app/api/settings.py:24-32`
- Unauthentifizierter Endpoint verraet ob Telegram konfiguriert ist
- **Aktion:** Hinter Auth schuetzen (wird durch 1.3 geloest)

---

## Phase 3 — Code-Qualitaet Backend (P2)

### 3.1 Konfiguration zentralisieren

Aktuell sind Magic Numbers ueber den gesamten Code verstreut:

| Wert | Datei | Zeile |
|------|-------|-------|
| Scheduler 1min/2min | `core/scheduler.py` | 76, 82 |
| `max_tokens=1000` | `services/ai.py` | 113 |
| `temperature=0.3` | `services/ai.py` | 114 |
| `MAX_CONCURRENT=3` | `scraper/httpclient.py` | 6 |
| Bargain-Threshold `>=8` | `services/ai.py` | 129 |

**Aktion:** Konstanten-Modul oder `AppSettings`-Erweiterung

### 3.2 Grosse Methoden aufteilen

| Methode | Datei | Zeilen | Vorschlag |
|---------|-------|--------|-----------|
| `parse_ad_detail()` | `parser.py` | 122-249 (128 Zeilen) | Aufteilen in `_parse_price()`, `_parse_seller()`, `_parse_images()` |
| `_analyze_ad()` | `ai.py` | 101-135 | Zerlegen in Fetch, API-Call, Parse, Notify |
| `_get_filter_reason()` | `scraper.py` | 85-123 | Separate Filter-Methoden pro Typ |

### 3.3 Error Handling vereinheitlichen

| Problem | Datei | Zeile | Aktion |
|---------|-------|-------|--------|
| Bare `except Exception` | `httpclient.py` | 20-24 | Spezifische Exceptions fangen |
| Job-Fehler nicht in DB | `scheduler.py` | 42-43 | ErrorLog-Eintraege erstellen |
| `assert` statt Validierung | `scraper.py` | 29 | Durch `ValueError` ersetzen |
| Fehlender URL-Kontext | `httpclient.py` | 23-24 | URL im Log-Eintrag ausgeben |
| Generisches Exception Catching | `scheduler.py` | 42-43, 58-59 | Spezifische Typen fangen |

### 3.4 Code-Duplikation entfernen
- **`httpclient.py:11-63`:** `_fetch_pages()` und `_fetch_binary()` fast identisch — generische `_fetch_concurrent()` Methode extrahieren
- **API-Router:** Aehnliche Query-Patterns in `ads.py`, `errorlogs.py`, `scraperuns.py` — Query-Builder Utility

### 3.5 Veraltete Patterns modernisieren
- `datetime.utcnow()` in `scheduler.py:27` und `scraper.py:56` — ersetzen durch `datetime.now(datetime.UTC)` (deprecated seit Python 3.12)
- `Optional["AdSearch"]` in `errorlog.py:25` — konsistent `|`-Syntax verwenden
- Ungenutzter Import `from typing import Optional` in `errorlog.py:2` entfernen

### 3.6 AI Service Separation of Concerns
- **Datei:** `app/services/ai.py`
- Vermischt aktuell: Text-Formatierung (Z.136), Image-Download (Z.180), Response-Parsing (Z.233), Preiskontext (Z.255), Notification (Z.134)
- **Aktion:** Verantwortlichkeiten in Hilfsmethoden oder separate Module aufteilen

### 3.7 Logging verbessern
- Mix aus f-Strings und %-Formatting — einheitlich auf `%`-Style (effizienter bei deaktivierten Log-Levels)
- Routine-Logs (`scheduler.py:24`) auf `DEBUG` statt `INFO`
- Sensible Werte (Telegram-Token) nicht in Logs ausgeben

---

## Phase 4 — Code-Qualitaet Frontend (P2)

### 4.1 TypeScript Build Errors nicht ignorieren
- **Datei:** `web/next.config.mjs:3-5`
- `ignoreBuildErrors: true` maskiert echte Fehler
- **Aktion:** Entfernen und tatsaechliche TS-Fehler beheben

### 4.2 Wiederholten Code extrahieren

| Duplikat | Dateien | Aktion |
|----------|---------|--------|
| ID-Extraktion aus URL | `ad-detail-page.tsx:37-40`, `search-detail-page.tsx:43-46` | Custom Hook `useIdFromPathname()` |
| Error Handling Pattern | 6+ Pages (identisches `e instanceof Error ? ...`) | Utility `handleApiError()` |
| Skeleton-Layouts | `page.tsx`, `ads/page.tsx`, `searches/page.tsx` etc. | Wiederverwendbare Skeleton-Komponenten |

### 4.3 Grosse Komponenten aufteilen
- **Datei:** `web/app/(app)/ads/page.tsx` (240 Zeilen)
- Vermischt Fetching, Filtering, Sorting, zwei View-Modes
- **Aktion:** Aufteilen in `AdsFilterBar`, `AdsGrid`, `AdsTable` + `useAdsFiltering()` Hook

### 4.4 Konstanten zentralisieren
- Score-Thresholds (`>=8`, `>=6`, `>=7`) in `format.ts` und `page.tsx` verstreut
- Seller-Ratings (0, 1, 2) implizit
- **Aktion:** `web/lib/constants.ts` erstellen:
  ```typescript
  export const SCORE_THRESHOLDS = { HIGH: 8, MEDIUM: 6 }
  export const BARGAIN_SCORE_THRESHOLD = 7
  export const SELLER_RATINGS = { POOR: 0, OK: 1, TOP: 2 }
  ```

### 4.5 Native Dialoge ersetzen
- **Dateien:** `search-card.tsx:52`, `search-detail-page.tsx:93`
- `window.confirm()` durch shadcn `AlertDialog` ersetzen

### 4.6 Image-Optimierung aktivieren
- **Datei:** `web/next.config.mjs:6-8`
- `images: { unoptimized: true }` deaktiviert Next.js Image Optimization
- **Aktion:** Aktivieren und erlaubte Domains konfigurieren

### 4.7 Inkonsistente CSS-Klassen
- **Datei:** `web/components/external-link.tsx:15`
- Template-Literal statt `cn()` Utility fuer Klassen-Verkettung
- **Aktion:** Konsistent `cn()` nutzen

### 4.8 Fehlende Loading States bei Mutationen
- **Datei:** `web/app/(app)/searches/page.tsx:46-66`
- `handleCreate()` und `handleDelete()` zeigen keinen Loading-State
- Mehrere Async-Operationen koennen gleichzeitig getriggert werden
- **Aktion:** Loading-State und Button-Disabling bei Mutationen

### 4.9 Typ-Sicherheit verbessern
- **Datei:** `ad-detail-page.tsx:42`
- `useState<Awaited<ReturnType<typeof fetchAd>> | null>` statt direktem `useState<Ad | null>`
- **Aktion:** Typen aus `types.ts` importieren

---

## Phase 5 — Architektur-Verbesserungen (P3)

### 5.1 Dependency Injection fuer Config
- **Dateien:** `app/api/settings.py:3`, `app/services/ai.py:9`
- `app_config` wird direkt importiert statt injiziert
- Erschwert Tests (nur via Monkey-Patching)
- **Aktion:** Config als Parameter an Services uebergeben

### 5.2 Transaktions-Scoping
- **Datei:** `app/services/scraper.py`
- Mehrere `session.commit()` Aufrufe (Zeilen 32, 58, 212)
- Bei Fehler zwischen Commits — inkonsistenter Zustand
- **Aktion:** Einzelne Transaktion mit `session.begin()` fuer Multi-Step-Operationen

### 5.3 Fehlende Tests ergaenzen

| Bereich | Status | Prioritaet |
|---------|--------|------------|
| ScraperService E2E (mit gemockten HTTP-Responses) | Fehlt | Hoch |
| TelegramService | Fehlt | Mittel |
| Scheduler-Logik | Fehlt | Niedrig |
| Frontend (komplett — kein einziger Test) | Fehlt | Mittel |

### 5.4 Performance-Risiken adressieren
- **N+1 Queries:** `ai.py:82-86` — jeder `_analyze_ad()` Aufruf queried `AdSearch` separat — Pre-Fetching
- **Memory:** `ai.py:257-262` — `_build_price_context()` laedt alle Ads ohne Limit — Aggregation in DB
- **Memory:** `httpclient.py:44-68` — Binaerdaten komplett im RAM — Groessenlimit einfuehren

### 5.5 Accessibility verbessern
- **Dateien:** `ad-detail-page.tsx:146-161`, `external-link.tsx`
- Fehlende `aria-label` Attribute bei Image-Gallery-Buttons und externen Links
- **Aktion:** Beschreibende ARIA-Labels hinzufuegen

---

## Zusammenfassung

| Phase | Fokus | Aufwand | Risiko wenn ignoriert |
|-------|-------|---------|----------------------|
| **P0** | API-Key revoken, CORS, Auth | 1-2 Tage | **Kritisch** — offene Angriffsflaeche |
| **P1** | SSRF-Schutz, Security Headers, Input-Validierung | 2-3 Tage | **Hoch** — exploitbar |
| **P2** | Code-Qualitaet Backend + Frontend | 3-5 Tage | Mittel — technische Schulden |
| **P3** | Architektur, Tests, DI, Performance | 3-5 Tage | Niedrig — Wartbarkeit |

---

## Positive Befunde

- Keine zirkulaeren Abhaengigkeiten — saubere Layer-Trennung
- Korrekte FastAPI Session-Verwaltung via Dependency Injection
- SQLModel ORM schuetzt vor SQL-Injection
- Models + API-Schemas co-located (Source of Truth an einem Ort)
- Gute Unit-Test-Abdeckung fuer Parser, Filter, AI-Service, API
- Scraper-Layer rein funktional (kein Business-Logic-Leaking)
- Typ-Hints ueberwiegend vorhanden
- Frontend nutzt konsistent shadcn/ui Komponenten
