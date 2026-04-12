# Web-Frontend (Next.js)

Das Frontend ist eine **Next.js 16**-App mit **React 19**, **Tailwind v4** und **shadcn/ui**. Sie wird **unabhängig vom Python-Backend** betrieben: lokal typischerweise auf Port 3000, in Produktion z. B. auf **Vercel**; die REST-API liegt auf **FastAPI** (lokal :8000, in Produktion z. B. Railway).

## Routen & Seiten

| Route | Beschreibung |
|-------|--------------|
| `/` | **Dashboard** – Übersicht: aktive Suchaufträge, Anzahl Angebote, letzte Schnäppchen, letzte Scrape-Läufe |
| `/searches` | **Suchaufträge** – Liste aller Suchen, Anlegen/Bearbeiten/Löschen, manueller Scrape-Start |
| `/searches/[id]` | **Suchauftrag-Detail** – Konfiguration, zugehörige Anzeigen, Scrape-Historie |
| `/ads` | **Anzeigen** – Alle Anzeigen mit Filter (Score, Suchauftrag, Analyse-Status), Sortierung, Grid/Listenansicht |
| `/ads/[id]` | **Anzeigen-Detail** – Titel, Preis, Bilder, Verkäufer, KI-Zusammenfassung, Bewertung |
| `/settings` | **Einstellungen** – Verkäufer-Filter, Mindestbewertung, Telegram |

## Struktur (web/)

- **`app/(app)/`** – Route-Gruppe mit gemeinsamem Layout (Sidebar, Breadcrumbs). Alle App-Seiten leben hier.
- **`app/layout.tsx`** – Root-Layout.
- **`app/(app)/layout.tsx`** – App-Layout mit `SidebarProvider`, `AppSidebar`, `SidebarInset`; mobil: Header mit Sidebar-Trigger.
- **`lib/api.ts`** – Alle API-Aufrufe (typisiert gegen `lib/types.ts`). Basis-URL über **`NEXT_PUBLIC_API_URL`** (vollständige API-Origin, z. B. `http://127.0.0.1:8000` lokal oder `https://api.example.com` in Produktion).
- **`lib/types.ts`** – TypeScript-Typen für Ad, AdSearch, ScrapeRun, AppSettings usw.
- **`lib/format.ts`** – Hilfsfunktionen (z. B. Datums-/Preisformatierung).
- **`components/`** – Wiederverwendbare UI: `app-sidebar`, `page-header`, `ad-card`, `search-card`, `score-badge`, `latest-deals`, `stat-card`, `empty-state`, `content-reveal` usw.
- **`components/ui/`** – shadcn/ui-Primitive (Button, Card, Dialog, Table, Sheet, …); nicht direkt anpassen.

## Wichtige Komponenten

- **AppSidebar** – Navigation (Dashboard, Suchaufträge, Schnäppchen, Einstellungen), immer sichtbar (Desktop) bzw. einklappbar (mobil).
- **PageHeader** – Titel + Untertitel pro Seite.
- **AdCard / SearchCard** – Karten für Anzeigen bzw. Suchaufträge mit Aktionen.
- **ScoreBadge** – Anzeige des KI-Bewertungswerts (0–10) mit farblicher Einordnung.
- **LatestDeals** – kompakte Liste der neuesten Schnäppchen auf dem Dashboard.

## Datenfluss

- Alle Daten kommen über **`lib/api.ts`** vom FastAPI-Backend (REST/JSON). Kein eigener Businesslogik-Code im Frontend.
- Seiten laden Daten in `useEffect`, nutzen lokalen State bzw. bei Bedarf erneutes Fetch nach Aktionen (z. B. nach Speichern oder Scrape-Start).

## Build & Dev

- **Entwicklung:** `npm run dev` — Next auf :3000; `uv run start` setzt `NEXT_PUBLIC_API_URL` auf die lokale API, wenn es den Dev-Server mitstartet.
- **Produktion (Vercel):** `npm run build` — Next-Produktionsbuild; `npm start` startet `next start` (Node). API-URL per `NEXT_PUBLIC_API_URL` auf die öffentliche API setzen.
