# Schnappster — UX & Design Verbesserungsplan

Erstellt am: 2026-03-07
Perspektive: Senior UX Designer

---

## Gesamtbewertung

Das UI ist funktional und visuell konsistent dank shadcn/ui + Tailwind. Die Amber-Farbpalette mit Stone-Neutraltoenen ergibt ein warmes, einladendes Design. Hauptprobleme liegen bei **fehlender Nutzerorientierung** (Onboarding, leere Zustaende, Feedback), **Barrierefreiheit** und **mobiler Optimierung**.

---

## Phase 1 — First-Time User Experience & Onboarding (Hoch)

### 1.1 Wartezeit nach erster Suche nicht kommuniziert
- **Problem:** Nach Erstellen der ersten Suche bleibt Ads-Seite leer. Nutzer weiss nicht, dass Scraper erst laufen muss.
- **Aktion:**
  - Empty State erweitern: "Deine Suche laeuft — erste Ergebnisse erscheinen in wenigen Minuten"
  - Nach Erstellen einer Suche, Scraper job automatisch ausführen
  - Optional: Fortschrittsanzeige oder letzter Scrape-Zeitstempel anzeigen

### 1.2 Fehlende Kontexthilfen in Formularen
- **Dateien:** `web/components/search-form.tsx`
- **Problem:** Felder wie "Prompt Addition" und "Blacklist-Keywords" haben keine Erklaerung
- **Aktion:**
  - Hilfe-Texte unter Feldern (`aria-describedby`):
    - Prompt Addition: "Zusaetzliche Anweisungen fuer die KI-Bewertung, z.B. 'Bevorzuge unbenutzte Artikel'"
    - Blacklist: "Kommagetrennte Begriffe, z.B. 'defekt, bastler, ersatzteil'"
    - Hilfe Symbol Icon mit Popup 
  - Intervall-Feld: Labels "5 Min = sehr haeufig, 1440 Min = taeglich"

### 1.3 Telegram-Einrichtung fuer Laien unverstaendlich
- **Datei:** `web/app/(app)/settings/page.tsx:144-149`
- **Problem:** Technische Begriffe (BOT_TOKEN, CHAT_ID) ohne Anleitung
- **Aktion:** Link zu Erklaerung

---

## Phase 2 — Feedback & Interaktionsmuster (Hoch)

### 2.1 Keine Lade-Zustaende bei Aktionen
- **Problem:** Erstellen, Loeschen, Aktualisieren zeigen keinen Loading-State. Buttons bleiben klickbar — Doppelsubmits moeglich.
- **Dateien:** `searches/page.tsx:46-66`, `search-detail-page.tsx:93-101`, `search-card.tsx:52`
- **Aktion:**
  - Spinner in Buttons waehrend API-Call
  - Button `disabled` setzen waehrend Mutation
  - Optimistic UI Updates fuer schnelleres Feedback

### 2.2 Native `window.confirm()` durch Custom Dialog ersetzen
- **Dateien:** `search-card.tsx:52`, `search-detail-page.tsx:93`
- **Problem:** Browser-native Dialoge sind unstylbar, brechen das Design, zeigen keine Konsequenzen
- **Aktion:**
  - shadcn `AlertDialog` nutzen
  - Kontext anzeigen: "Diese Suche und alle zugehoerigen Angebote werden geloescht"
  - Destructive-Button-Variante fuer Loeschen

### 2.3 Generische Fehlermeldungen
- **Problem:** "Daten konnten nicht geladen werden" ohne Kontext (Netzwerk? Server? Auth?)
- **Dateien:** 6+ Pages mit identischem Pattern
- **Aktion:**
  - Netzwerkfehler: "Keine Verbindung zum Server — bitte Internetverbindung pruefen"
  - Serverfehler: "Serverfehler — bitte spaeter erneut versuchen"
  - "Erneut laden" Button in Error States

### 2.4 Loeschen-Button nur bei Hover sichtbar
- **Datei:** `search-card.tsx:56-60`
- **Problem:** `opacity-0 group-hover:opacity-100` — auf Touch-Geraeten kein Hover, Button unerreichbar
- **Aktion:** Immer sichtbar machen (ggf. subtiler gestylt) oder Drei-Punkte-Menue

---

## Phase 3 — Formular-UX verbessern (Hoch)

### 3.1 Keine Echtzeit-Validierung
- **Datei:** `web/components/search-form.tsx`
- **Problem:** Validation erst bei Submit (HTML5 only). Keine Inline-Fehlermeldungen.
- **Aktion:**
  - `react-hook-form` + `zod` Integration (bereits in Dependencies)
  - Inline-Fehlermeldungen unter Feldern in Rot
  - URL-Feld: Validierung auf Domains von `kleinanzeigen.de` Suchergebnislisten
  - Preis-Felder: Min darf nicht groesser als Max sein

### 3.2 Blacklist-Keywords als Tags statt Freitext
- **Datei:** `search-form.tsx:125-133`
- **Problem:** Kommagetrennte Keywords in einem Input — Nutzer sieht nicht, wie viele Keywords erkannt werden
- **Aktion:**
  - Tag-Input: Keywords als entfernbare Chips/Tags anzeigen
  - Visuelles Feedback: "3 Keywords aktiv"
  - Enter-Taste fuegt Tag hinzu

### 3.3 Ungespeicherte Aenderungen beim Schliessen
- **Problem:** Dialog-Schliessung verwirft Formulardaten ohne Warnung
- **Aktion:** "Ungespeicherte Aenderungen verwerfen?" Dialog bei Dirty-State

### 3.4 Intervall-Eingabe verbessern
- **Problem:** Zahlenfeld 5-1440 ohne Kontextverstaendnis (Minuten)
- **Aktion:**
  - Einheit "Minuten" neben dem Feld anzeigen
  - Preset-Buttons: "5 Min", "10 Min", "30 Min", "1 Std", "6 Std", "Taeglich"
  - Oder Slider mit beschrifteten Markierungen

---

## Phase 4 — Navigation & Informationsarchitektur (Mittel)

### 4.1 Defekter Logs-Link in Sidebar
- **Datei:** `app-sidebar.tsx:22`
- **Problem:** Navigation verweist auf `/logs/` Route — Seite existiert nicht
- **Aktion:** Fehler prüfen

### 4.2 Fehlende Breadcrumb-Navigation
- **Problem:** Detail-Seiten zeigen nur Zurueck-Button, keine vollstaendige Pfadnavigation
- **Aktion:**
  - Breadcrumbs: "Dashboard > Suchen > iPhone Berlin"
  - Klickbar fuer schnelle Navigation zwischen Ebenen

### 4.3 Keine Pagination oder Virtualisierung
- **Problem:** Alle Ads werden auf einmal geladen und gerendert. Bei hunderten Ads — Performance-Probleme.
- **Dateien:** `ads/page.tsx`, `search-detail-page.tsx`
- **Aktion:**
  - Pagination mit Seitennavigation (20-50 Ads pro Seite)
  - Gesamtanzahl anzeigen: "Zeige 1-20 von 142 Angeboten"

### 4.4 Filter-Zustand geht bei Reload verloren
- **Problem:** Score-Filter, Suche-Filter, Sortierung werden nicht in URL oder localStorage gespeichert
- **Aktion:** Filter-State in URL-Searchparams speichern (`?minScore=7&sort=score`)
  - Ermoeglicht Bookmarking und Teilen gefilterter Ansichten

---

## Phase 5 — Datenvisualisierung & Informationshierarchie (Mittel)

### 5.1 Score-Legende fehlt
- **Datei:** `score-badge.tsx`, `format.ts:28-32`
- **Problem:** Farbskala (rot < 6, amber 6-8, gruen 8+) wird nirgends erklaert. Nutzer raet, was ein "guter" Score ist.
- **Aktion:**
  - Tooltip auf Score-Badge: "8+ = Top-Schnaeppchen, 6-8 = Guter Deal, < 6 = Normaler Preis"
  - Oder Legende auf der Ads-Seite

### 5.2 Abgeschnittene Texte ohne Tooltip
- **Problem:** `line-clamp-1/2` und `truncate` schneiden Titel und AI-Summaries ab. Kein Tooltip zum Lesen.
- **Dateien:** `ad-card.tsx`, `latest-deals.tsx`, Tabellen-Views
- **Aktion:** `title` Attribut oder Tooltip-Komponente fuer abgeschnittene Texte

### 5.3 AI-Analyse nur auf Klick sichtbar
- **Datei:** `ad-detail-page.tsx:280-292`
- **Problem:** AI-Reasoning ist in einem Collapsible versteckt. Nutzer verpassen wichtige Informationen.
- **Aktion:** Standardmaessig geoeffnet anzeigen oder prominenter platzieren

---

## Phase 6 — Image Gallery & Medien (Mittel)

### 6.1 Bildergalerie nicht nutzbar
- **Datei:** `ad-detail-page.tsx:143-164`
- **Problem:**
  - Nur Klick auf Thumbnails — keine Pfeiltasten-Navigation
  - Kein Prev/Next Button
  - Kein Swipe auf Mobilgeraeten
  - Kein Vollbild/Lightbox-Modus
- **Aktion:**
  - Pfeil-Buttons links/rechts auf Hauptbild
  - Keyboard-Navigation (ArrowLeft/ArrowRight)
  - Touch-Swipe Support
  - Klick auf Hauptbild oeffnet Lightbox

### 6.2 Kaputte Bilder ohne Fallback
- **Problem:** Wenn Kleinanzeigen-Bild-URLs ablaufen oder 404 liefern, bleibt leerer Bereich
- **Aktion:**
  - `onError` Handler auf `<Image>` Tags
  - Fallback-Platzhalter mit "Bild nicht verfuegbar" Nachricht
  - Package-Icon als visueller Ersatz

---

## Phase 7 — Mobile Optimierung (Mittel)

### 7.1 Filter-Leiste nicht mobiltauglich
- **Datei:** `ads/page.tsx:170-189`
- **Problem:** 4 Filter-Controls (Score, Suche, Sort, View) wrappen unschoen auf kleinen Screens
- **Aktion:**
  - Mobile: "Filter" Button der ein Sheet/Bottomsheet oeffnet
  - Desktop: Weiterhin inline

### 7.2 Tabellen-View auf Mobile unbrauchbar
- **Problem:** Table-View erfordert horizontales Scrollen auf Mobile
- **Aktion:**
  - Tabellen-View auf Mobile automatisch auf Karten umschalten
  - Oder responsive Tabelle mit gestapelten Zeilen

### 7.3 Touch-Targets zu klein
- **Problem:** Icon-Buttons mit `size="icon-sm"` (32px) sind unter WCAG Minimum (48x48px)
- **Dateien:** View-Toggle-Buttons, Filter-Controls
- **Aktion:** Mindestens 44x44px Touch-Targets auf Mobile (`min-h-11 min-w-11`)

### 7.4 Sidebar-Oeffnung nicht erkennbar
- **Datei:** `layout.tsx:9-10`
- **Problem:** Auf Mobile ist nur ein Hamburger-Icon sichtbar. Kein visueller Hinweis, dass es ein Menue gibt.
- **Aktion:** Hamburger-Icon prominenter gestalten oder Bottom-Navigation fuer Mobile

---

## Phase 8 — Barrierefreiheit / Accessibility (Mittel)

### 8.1 Farbe als einziges Unterscheidungsmerkmal
- **Problem:** Score-Badges nutzen nur Farbe (rot/amber/gruen) — nicht fuer Farbenblinde geeignet
- **Aktion:**
  - Icons zusaetzlich: Pfeil-Hoch (gruen), Waagerecht (amber), Pfeil-Runter (rot)
  - Oder Pattern/Textur-Unterschiede

### 8.2 Fehlende ARIA Live Regions
- **Problem:** Toast-Benachrichtigungen werden nicht an Screenreader kommuniziert
- **Aktion:** `aria-live="polite"` auf Toast-Container

### 8.3 Kein Skip-Link
- **Problem:** Kein "Zum Hauptinhalt springen" Link fuer Keyboard-Nutzer
- **Aktion:** Hidden Skip-Link als erstes Element im Body

### 8.4 Dialog Focus Management
- **Problem:** SearchForm-Dialog fangen Focus nicht korrekt (kein Focus-Trap, kein Focus-Return)
- **Aktion:** shadcn Dialog sollte das bereits tun — sicherstellen, dass es korrekt implementiert ist

### 8.5 Fehlende ARIA Labels
- **Dateien:** `ad-detail-page.tsx:146-161`, `external-link.tsx`
- **Problem:** Bild-Gallery-Buttons und externe Links ohne beschreibende Labels
- **Aktion:** `aria-label="Naechstes Bild"`, `aria-label="Auf Kleinanzeigen oeffnen (neues Fenster)"`

---

## Phase 9 — Design-System Konsistenz (Niedrig)

### 9.1 Inkonsistente Empty States
- **Problem:** Manche Pages nutzen `EmptyState` Komponente, andere inline-Text in Tabellen
- **Aktion:** Einheitlich `EmptyState` mit Icon, Message und optionalem CTA ueberall nutzen

### 9.2 Inkonsistente Button-Varianten
- **Problem:** Zurueck-Buttons mal `ghost`, mal `outline` — keine klare Regel
- **Aktion:** Styleguide definieren:
  - Primaere Aktion: `default` (Amber)
  - Sekundaere Aktion: `outline`
  - Tertiaere/Navigation: `ghost`
  - Destruktiv: `destructive`

### 9.3 AI-Analyse-Box Sonderbehandlung
- **Datei:** `ad-detail-page.tsx`
- **Problem:** Nur AI-Box hat farbigen Rand (`border-amber-200 bg-amber-50/50`). Inkonsistent mit anderen Cards.
- **Aktion:** Entweder als Designmuster fuer "besondere" Karten definieren oder angleichen

### 9.4 Badge/Status-Darstellung uneinheitlich
- **Problem:** Aktiv-Status mal als Badge, mal als farbiger Text. Intervall mal als Badge, mal als Plain-Text.
- **Aktion:** Konsistentes Pattern: Status immer als Badge, Konfigurationswerte als Text

### 9.5 CSS-Klassen-Verkettung inkonsistent
- **Datei:** `external-link.tsx:15`
- **Problem:** Template-Literal statt `cn()` Utility
- **Aktion:** Durchgehend `cn()` aus `lib/utils.ts` nutzen
