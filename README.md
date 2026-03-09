# Schnappster

> Ein persönlicher Kleinanzeigen.de Schnäppchen-Finder mit KI-Analyse

Schnappster ist eine Web-App, die periodisch deine gespeicherten Kleinanzeigen-Suchergebnisse durchsucht, neue Angebote automatisch auf Schnäppchen analysiert und die Ergebnisse in einem übersichtlichen Dashboard anzeigt.

## Features

- **Automatisches Scraping** – Durchsucht Kleinanzeigen.de Suchergebnisse in konfigurierbaren Intervallen
- **KI-Analyse** – Bewertet Angebote mit Hilfe von KI (OpenAI-kompatible API, z. B. OpenRouter oder Alibaba Model Studio) auf Basis von Preis, Zustand und Verkäuferbewertung
- **Vergleichspreise** – Berücksichtigt automatisch Preise ähnlicher Angebote aus derselben Suche
- **Telegram-Benachrichtigungen** – Benachrichtigt dich bei echten Schnäppchen (Score 8+)
- **Filter & Blacklists** – Filtert nach Preisbereich, schwarzen Keywords und Verkäufer-Typen
- **Dashboard** – Übersichtliche Web-Oberfläche mit Sortier- und Filtermöglichkeiten

## Tech Stack

### Backend
- **Python 3.13** mit FastAPI
- **SQLModel** (SQLite) für Datenbank
- **curl-cffi** für HTTP-Requests (Browser-Impersonation)
- **BeautifulSoup4** für HTML-Parsing
- **APScheduler** für Hintergrundaufgaben
- **OpenAI-kompatible API** für KI-Analyse (z. B. OpenRouter, Alibaba Model Studio Coding Plan)

### Frontend
- **Next.js 16** + React 19
- **Tailwind CSS v4**
- **shadcn/ui** Komponenten

## Installation

### Voraussetzungen

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) Package Manager
- Node.js 20+ (für Frontend)
- OpenRouter API Key oder anderer OpenAI-kompatibler API-Key

### 1. Repository klonen

```bash
git clone https://github.com/Pikktee/schnappster.git
cd schnappster
```

### 2. Backend einrichten

```bash
# Installation mit uv
uv sync

# Umgebungsvariablen konfigurieren
cp .env.example .env
# OPENAI_API_KEY, OPENAI_MODEL und optional OPENAI_BASE_URL in .env setzen
```

### 3. Frontend einrichten (optional)

```bash
cd web
npm install
npm run build
```

## Konfiguration

### Umgebungsvariablen (.env)

Bis März 2026 hießen die Variablen `OPENROUTER_API_KEY` und `OPENROUTER_AI_MODEL`; sie wurden durch `OPENAI_API_KEY`, `OPENAI_MODEL` und optional `OPENAI_BASE_URL` ersetzt. Bestehende `.env` bitte entsprechend anpassen.

```env
# OpenAI-kompatible API (erforderlich). Base-URL optional, Default: OpenRouter.
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=meta-llama/llama-3.1-70b-instruct
# Optional, z. B. für Alibaba Model Studio: OPENAI_BASE_URL=https://coding-intl.dashscope.aliyuncs.com/v1

# Telegram Benachrichtigungen (optional)
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

### Einstellungen in der App

Über die Settings-Seite können folgende Optionen konfiguriert werden:
- Verkäufer-Filter (nur gewerbliche/privat)
- Mindestverkäuferbewertung
- Telegram-Benachrichtigungen

## Verwendung

### Server starten

```bash
# Mit Tests vorher
uv run start

# Ohne Tests
uv run start --skip-tests
```

Der Server startet auf http://localhost:8000

### CLI Commands

| Command | Beschreibung |
|---------|-------------|
| `uv run start` | Startet den FastAPI Server |
| `uv run scrape [adsearch_id]` | Manueller Scraping-Start |
| `uv run analyze [limit]` | Manuelle KI-Analyse starten |
| `uv run dbreset` | Datenbank zurücksetzen (bei Schema-Änderungen) |
| `uv run pytest` | Tests ausführen |
| `uv run ruff check .` | Code linting |
| `uv run ruff format .` | Code formatieren |

### Suchauftrag erstellen

1. Öffne das Dashboard im Browser
2. Klicke auf "Neue Suche erstellen"
3. Füge die URL deiner Kleinanzeigen-Suche ein
4. Konfiguriere Intervall, Preisbereich und Blacklist
5. Speichern – der Scraper läuft automatisch im Hintergrund

## Architektur

```
schnappster/
├── app/
│   ├── api/           # FastAPI Router (REST Endpoints)
│   ├── core/          # DB, Scheduler, Settings, Logging
│   ├── models/        # SQLModel Tabellen & Schemas
│   ├── scraper/       # HTTP Client & HTML Parser
│   └── services/      # Business Logic (Scraper, AI, Settings)
├── cli/               # CLI Entry Points
├── web/               # Next.js Frontend
├── docs/              # Projekt-Dokumentation
└── data/              # SQLite Datenbank
```

### Scraping Pipeline

1. **Preview List** – Suchergebnisseite parsen, neue Ads identifizieren
2. **Detail Pages** – Detailseiten parallel laden
3. **Filtering** – Preis, Keywords, Verkäufer-Typ, Bewertung
4. **Speichern** – Neue Ads in der Datenbank speichern
5. **KI-Analyse** – Separate Analyse mit Vergleichspreisen (alle 2 Min)

### Scheduler (APScheduler)

| Job | Intervall | Beschreibung |
|-----|-----------|-------------|
| `check_and_scrape` | 1 Minute | Prüft aktive Suchaufträge und scraped fällige |
| `analyze_ads` | 2 Minuten | Analysiert bis zu 10 unverarbeitete Ads mit KI |

Beide Jobs laufen auch einmal direkt beim Start.

## Datenbank-Modelle

| Modell | Beschreibung |
|--------|-------------|
| **AdSearch** | Suchauftrag (Name, URL, Intervall, Filter, is_active) |
| **Ad** | Einzelanzeige (Titel, Preis, Bilder, Verkäufer, bargain_score, ai_summary) |
| **ScrapeRun** | Scrape-Protokoll (ads_found, ads_new, status) |
| **ErrorLog** | Fehler-Protokoll (error_type, message, details) |
| **AppSettings** | Key-Value Store für Runtime-Settings |

### Bargain Score

Die KI bewertet Angebote von 0–10:
- **0–2**: Überteuert oder verdächtig
- **3–4**: Leicht überteuert
- **5**: Normaler Gebrauchtpreis (die meisten Angebote)
- **6**: Leicht unter Marktpreis
- **7**: Gutes Angebot
- **8–9**: Echtes Schnäppchen
- **10**: Unglaublich günstig (sehr selten)

## Entwicklung

### Tests ausführen

```bash
uv run pytest
uv run pytest tests/test_parser.py  # Einzelner Test
```

### Code Qualität

```bash
uv run ruff check .
uv run ruff format .
```

### Datenbank zurücksetzen

Bei Schema-Änderungen (kein Alembic vorhanden):

```bash
uv run dbreset
```

⚠️ **Achtung**: Löscht alle Daten!

## Dokumentation

- [IMPROVEMENT_PLAN.md](docs/IMPROVEMENT_PLAN.md) — Architektur-Review & Verbesserungsplan
- [UX_DESIGN_PLAN.md](docs/UX_DESIGN_PLAN.md) — UX & Design Verbesserungen
- [schnappster-context.md](docs/schnappster-context.md) — Projekt-Kontext