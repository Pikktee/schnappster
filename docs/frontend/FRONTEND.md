# Web-Frontend (Next.js)

Das Frontend ist eine **Next.js 16**-App mit **React 19**, **Tailwind v4** und **shadcn/ui**. Es wird als statischer Export (`web/out/`) gebaut und von FastAPI unter derselben Origin ausgeliefert.

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
- **`lib/api.ts`** – Alle API-Aufrufe (typisiert gegen `lib/types.ts`). Basis-URL über `NEXT_PUBLIC_API_URL` (leer = Same-Origin).
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

- Alle Daten kommen über **`lib/api.ts`** vom Backend (`/api/...`). Kein eigener Backend-Businesslogik-Code im Frontend.
- Seiten laden Daten in `useEffect`, nutzen lokalen State bzw. bei Bedarf erneutes Fetch nach Aktionen (z. B. nach Speichern oder Scrape-Start).

## Build & Dev

- **Produktion:** `npm run build` (bzw. `npm run export`) erzeugt statischen Export in `web/out/`. FastAPI mountet dieses Verzeichnis und liefert es aus.
- **Entwicklung:** `npm run dev` startet den Next-Dev-Server (z. B. :3000); API-Anfragen gehen per CORS an den Backend-Server (:8000). Siehe Architektur-Diagramm „Development“.
