# Schnappster – Chrome-Erweiterung

Fügt die aktuelle Kleinanzeigen-Suchergebnisseite per Klick als Suchauftrag in Schnappster hinzu.

## Installation

1. Chrome öffnen und `chrome://extensions` aufrufen
2. „Entwicklermodus“ aktivieren (oben rechts)
3. „Entpackte Erweiterung laden“ wählen und den Ordner `extensions/chrome` aus dem Schnappster-Projektverzeichnis auswählen

## Nutzung

- Auf einer **Kleinanzeigen-Suchergebnisseite** (z. B. `https://www.kleinanzeigen.de/s-audio-hifi/60325/podmic/k0c172l4305r250`) ist das Schnappster-Icon in der Toolbar aktiv (nicht ausgegraut).
- **Ein Klick** auf das Icon sendet die aktuelle URL an das Schnappster-Backend und legt einen neuen Suchauftrag an (Name = Seitentitel oder „Kleinanzeigen-Suche“).
- Erfolg oder Fehler wird per Chrome-Benachrichtigung angezeigt.

## Einstellungen

- **Rechtsklick** auf das Extension-Icon → **Optionen**, oder unter `chrome://extensions` bei „Schnappster“ auf **Details** → **Erweiterungsoptionen**.
- **Base-URL**: Adresse des Schnappster-Backends (Standard: `http://localhost:8000`). Ohne abschließenden Schrägstrich eingeben.

## Hinweis

Das Backend muss CORS für die Extension erlauben (im Schnappster-Projekt ist die CORS-Middleware bereits eingebaut).
