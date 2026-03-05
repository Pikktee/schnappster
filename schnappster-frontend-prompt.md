# Schnappster Frontend – Cursor Prompt

## Projektübersicht

Erstelle das Frontend für **Schnappster**, eine Web-App die Kleinanzeigen.de-Suchergebnisse scrapt, mit KI analysiert und Schnäppchen identifiziert. Das Frontend kommuniziert mit einer bestehenden FastAPI REST-API unter `http://localhost:8000/api`.

Das Frontend-Projekt wird im Ordner `frontend/` angelegt (neben dem bestehenden `backend/`-Ordner).

## Tech Stack

- **Vue 3** mit Composition API und `<script setup>` Syntax
- **TypeScript**
- **Naive UI** als Komponentenbibliothek (https://www.naiveui.com/)
- **Vue Router** für Navigation
- **Vite** als Build-Tool

Kein Tailwind CSS – Naive UI bringt sein eigenes Styling mit. Zusätzliches Styling über Scoped CSS in den Komponenten.

## Design-Prinzipien

- **Helles Theme** – kein Dark Mode erforderlich
- **Warm und einladend**: Weiches Farbschema mit Amber/Orange-Akzenten
- **Dashboard-Stil**: Clean, aufgeräumt, funktional – inspiriert von Notion oder Linear
- **Polierte UX**: Korrekte Cursor-States (pointer bei klickbaren Elementen), Hover-Effekte, sanfte Transitions
- **Responsive**: Desktop-first, aber auf Tablet und Mobile nutzbar
- **Deutsche UI-Texte**

## Farbschema & Theme

Naive UI Theme-Override konfigurieren:

- Primärfarbe: Warmes Orange/Amber (#F59E0B / #D97706)
- Hintergrund: Sanftes Warmgrau (#FAFAF9)
- Karten: Weiß (#FFFFFF) mit subtilen Schatten
- Schnäppchen (Bargain Score 8-10) farblich hervorheben.
- Text: Dunkelgrau (#1C1917) für Haupttext, (#78716C) für Sekundärtext

```typescript
// Naive UI Theme Override
import { createTheme } from 'naive-ui'

const themeOverrides = {
  common: {
    primaryColor: '#F59E0B',
    primaryColorHover: '#D97706',
    primaryColorPressed: '#B45309',
    bodyColor: '#FAFAF9',
    cardColor: '#FFFFFF',
    textColorBase: '#1C1917',
    borderRadius: '8px',
  }
}
```

## Seitenstruktur

### Layout (App Shell)

- **Sidebar links** (einklappbar via n-layout-sider): Logo "Schnappster" oben mit kleinem Flammen- oder Schnäppchen-Icon, Navigation mit n-menu (Start, Suchaufträge, Anzeigen, Logs, Einstellungen), unten Versionsnummer v0.1.0
- **Hauptbereich rechts** (n-layout-content): Rendert die aktuelle Route
- **Kein separater Top Bar** – Seitentitel als h1 im Content-Bereich

### Dashboard (`/`)

- **Statistik-Karten** oben (n-grid mit n-card): Anzahl aktive Suchen, bestes Schnäppchen (höchster Bargain Score), Info wann der letzte Scraper aktiv war (z.B. "Aktualisiert vor 5 Min.")
- **Letzte Schnäppchen**: Die zuletzt gefundenen Angebote mit Score >= 7, sortiert nach Datum, als kompakte Karten-Liste

### Suchaufträge-Übersicht (`/searches`)

- Liste aller AdSearches als n-card Karten in einem Grid
- Pro Suche: Name (groß), URL (gekürzt/truncated), Intervall, letzte Scrape-Zeit als relative Zeit, Anzahl Angebote, Status-Badge aktiv/inaktiv (n-tag)
- "Neue Suche erstellen"-Button (n-button, primary) oben rechts → öffnet n-modal mit Formular
- Klick auf Karte → Detailseite
- Löschen über Icon-Button auf der Karte (mit n-popconfirm Bestätigung)

### Suchaufträge-Detailansicht (`/searches/:id`)

- **Header**: Name als Titel, Edit-Button (öffnet Modal), Löschen-Button (mit Bestätigung), Aktiv/Inaktiv-Toggle (n-switch)
- **Konfiguration**: Bearbeitbares Formular in n-card (Name, URL, Scrape-Intervall in Minuten, Min/Max Preis, Blacklist-Keywords, Prompt-Addition als Textarea)
- **Angebote-Liste**: Alle Ads dieser Suche als Karten oder Tabelle (umschaltbar)

### Angebote-Übersicht (`/ads`)

- **Filter-Leiste** oben: Mindest-Score (n-slider oder n-input-number), Suchauftrag-Dropdown (n-select), Sortierung (Datum, Preis, Score)
- **Darstellung umschaltbar**: Cards Grid (Standard) oder Tabelle (n-data-table)
- **Card-Layout pro Angebot** (n-card):
  - Vorschaubild links (erstes Bild aus image_urls, Fallback-Placeholder wenn leer)
  - Titel (fett, als Link zu Kleinanzeigen – mit externem Link-Icon)
  - Preis groß und prominent
  - Standort (PLZ + Stadt) kleiner darunter
  - Bargain Score als farbiger runder Badge
  - KI-Zusammenfassung (2–3 Zeilen, grau)
  - Verkäufer-Info kompakt (Name, Rating als farbiger Tag)

### Angebote-Detailansicht (`/ads/:id`)

- **Bildergalerie** oben (n-carousel oder einfaches Grid der Bilder)
- **Titel und Preis** prominent
- **Verkäufer-Box** (n-card): Name (als externer Link zur Verkäuferseite), Rating als farbiger Tag (TOP=grün, OK=gelb, Na ja=rot), Badges (Freundlich, Zuverlässig als n-tag), Typ (Privat/Gewerblich), Aktiv seit
- **Details**: Zustand, Versandkosten, Standort
- **Beschreibung**: Volltext in n-card mit whitespace-pre-wrap
- **KI-Analyse Box** (hervorgehobene n-card mit leichtem Orange-Hintergrund):
  - Bargain Score als große Zahl (farbig nach Score-Range)
  - KI-Zusammenfassung
  - KI-Begründung (aufklappbar via n-collapse)
- **Link zum Original** auf Kleinanzeigen.de (n-button mit externem Link-Icon)
- Löschen möglich (n-button danger mit n-popconfirm)

### Logs (`/logs`)

- Zwei Tabs (n-tabs): "Scrape-Durchläufe" und "Fehler"
- **Scrape-Durchläufe**: n-data-table mit Spalten: Zeitpunkt, Suchauftrag-Name, Gefunden, Neu, Status (als farbiger Tag)
- **Fehler**: n-data-table mit Spalten: Zeitpunkt, Typ, Nachricht, Details (aufklappbar)

### Einstellungen (`/settings`)

- n-card mit Formular
- Wenn `openrouter_api_key` nicht gesetzt: n-alert Hinweis mit Setup-Anleitung
- OpenRouter API Key (n-input type="password")
- KI-Modell (n-select mit Optionen)
- Speichern-Button mit Erfolgs-/Fehlermeldung (n-message)

## API-Endpoints

Backend auf `http://localhost:8000`, alle Endpoints unter `/api`:

```
GET    /health                         → { status: "ok" }

GET    /api/adsearches/                → AdSearch[]
POST   /api/adsearches/                → AdSearch erstellen
GET    /api/adsearches/{id}            → AdSearch
PATCH  /api/adsearches/{id}            → AdSearch aktualisieren (body: partielle Felder)
DELETE /api/adsearches/{id}            → AdSearch löschen

GET    /api/ads/                       → Ad[] (query params: adsearch_id, is_analyzed)
GET    /api/ads/{id}                   → Ad

GET    /api/scraperuns/                → ScrapeRun[] (query params: adsearch_id, limit)
GET    /api/errorlogs/                 → ErrorLog[] (query params: adsearch_id, limit)

GET    /api/settings/                  → AppSetting[]
GET    /api/settings/{key}             → AppSetting
PUT    /api/settings/{key}             → Setting aktualisieren (body: { value: "..." })
```

## TypeScript Interfaces

```typescript
interface AdSearch {
  id: number
  name: string
  url: string
  prompt_addition: string | null
  min_price: number | null
  max_price: number | null
  blacklist_keywords: string | null
  is_exclude_images: boolean
  is_active: boolean
  scrape_interval_minutes: number
  created_at: string
  last_scraped_at: string | null
}

interface Ad {
  id: number
  external_id: string
  title: string
  description: string | null
  price: number | null
  postal_code: string | null
  city: string | null
  url: string
  image_urls: string | null       // comma-separated URLs
  condition: string | null
  shipping_cost: string | null
  seller_name: string | null
  seller_url: string | null
  seller_rating: number | null    // 2=TOP, 1=OK, 0=Na ja
  seller_is_friendly: boolean
  seller_is_reliable: boolean
  seller_type: string | null      // "Privat" or "Gewerblich"
  seller_active_since: string | null
  adsearch_id: number
  bargain_score: number | null    // 0-10
  ai_summary: string | null
  ai_reasoning: string | null
  is_analyzed: boolean
  first_seen_at: string
}

interface ScrapeRun {
  id: number
  adsearch_id: number
  started_at: string
  finished_at: string | null
  ads_found: number
  ads_new: number
  status: string                  // "running", "completed", "failed"
}

interface ErrorLog {
  id: number
  adsearch_id: number | null
  error_type: string
  message: string
  details: string | null
  created_at: string
}

interface AppSetting {
  key: string
  value: string
}
```

## Projektstruktur

```
frontend/
├── src/
│   ├── api/
│   │   └── client.ts         # Fetch-Wrapper mit Error-Handling
│   ├── components/
│   │   ├── layout/           # AppLayout, Sidebar
│   │   ├── ads/              # AdCard, AdGrid, AdTable, ScoreBadge
│   │   ├── searches/         # SearchCard, SearchForm
│   │   └── common/           # Wiederverwendbare Komponenten
│   ├── composables/          # useAds, useSearches, useSettings, useTimeAgo
│   ├── router/
│   │   └── index.ts
│   ├── types/
│   │   └── index.ts          # TypeScript Interfaces
│   ├── views/
│   │   ├── DashboardView.vue
│   │   ├── SearchesView.vue
│   │   ├── SearchDetailView.vue
│   │   ├── AdsView.vue
│   │   ├── AdDetailView.vue
│   │   ├── LogsView.vue
│   │   └── SettingsView.vue
│   ├── App.vue
│   └── main.ts
├── index.html
├── package.json
├── tsconfig.json
└── vite.config.ts
```

## Vite Proxy Konfiguration

```typescript
// vite.config.ts
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
    }
  }
})
```

## Wichtige Hinweise

- `image_urls` ist ein comma-separated String → im Frontend splitten: `ad.image_urls?.split(',') ?? []`
- Bilder von `img.kleinanzeigen.de` funktionieren als `<img>` Tags (kein CORS-Problem)
- `seller_rating` ist ein Integer: 2=TOP, 1=OK, 0=Na ja → im Frontend mappen
- KI-Analyse-Felder (`bargain_score`, `ai_summary`, `ai_reasoning`) sind zunächst null → "Noch nicht analysiert" als Placeholder mit n-empty oder n-result anzeigen
- Fehlerbehandlung: n-message für Toast-Notifications bei API-Fehlern
- Loading States: n-skeleton für Listen und Karten
- Leere Zustände: n-empty mit freundlichen Meldungen und Handlungsaufforderung
- Alle klickbaren Elemente müssen `cursor: pointer` haben
- Relative Zeitangaben nutzen (z.B. "vor 5 Minuten" statt ISO-Timestamp)

## UX-Details die nicht vergessen werden dürfen

- Klickbare Karten: Gesamte Karte ist klickbar, nicht nur der Titel
- Hover-States: Subtiler Shadow/Scale-Effekt auf Karten beim Hovern
- Cursor: `pointer` auf allen interaktiven Elementen
- Externe Links: Immer mit Icon markieren und in neuem Tab öffnen
- Löschen: Immer mit Bestätigungsdialog (n-popconfirm)
- Leere Listen: Freundliche Illustration/Text + Call-to-Action Button
- Loading: Skeleton-Loader die die Form des Inhalts widerspiegeln
- Preise: Immer mit € formatiert, Tausendertrennzeichen mit Punkt (1.234,56 €)
- Scores: Immer farbcodiert (rot/gelb/grün) und mit einer Nachkommastelle

## Reihenfolge

1. Vite + Vue 3 + TypeScript Projekt im Ordner `frontend/` initialisieren
2. Naive UI installieren und Theme konfigurieren
3. Router und Layout (Sidebar + Hauptbereich) erstellen
4. API-Client mit Error-Handling erstellen
5. Dashboard implementieren
6. Suchaufträge-Übersicht und Detail implementieren
7. Angebote-Übersicht und Detail implementieren
8. Logs implementieren
9. Einstellungen implementieren