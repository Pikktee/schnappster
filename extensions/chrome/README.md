# Schnappster – Chrome-Erweiterung

Zwei Funktionen per Klick auf das Schnappster-Icon, je nachdem, wo du gerade bist:

- **Kleinanzeigen-Suchergebnisseite** → legt die Seite als **Suchauftrag** in Schnappster an.
- **Kleinanzeigen-Anzeigenseite** (`/s-anzeige/…`) → erzeugt per KI eine **Verhandlungsnachricht** und fügt sie direkt in das Nachrichtenfeld der Anzeige ein (mit vorgeschlagenem Gebot). Du prüfst sie und sendest selbst.

## Installation

1. Chrome öffnen und `chrome://extensions` aufrufen
2. „Entwicklermodus" aktivieren (oben rechts)
3. „Entpackte Erweiterung laden" wählen und den Ordner `extensions/chrome` aus dem Schnappster-Projektverzeichnis auswählen

## Einrichtung (einmalig)

**Rechtsklick** auf das Extension-Icon → **Optionen** (oder unter `chrome://extensions` bei „Schnappster" → **Details** → **Erweiterungsoptionen**):

1. **Base-URL** des Backends eintragen (Standard: `http://localhost:8000`, ohne abschließenden Schrägstrich) und speichern.
2. **Anmelden** mit deinem Schnappster-Konto (E-Mail + Passwort). Es wird nur ein Zugriffs-Token gespeichert, **nicht dein Passwort**. Das Token gilt 7 Tage; danach einfach neu anmelden.

## Nutzung

- Auf einer **Suchergebnisseite** ist das Icon aktiv → **Klick** legt den Suchauftrag an.
- Auf einer **Anzeigenseite** ist das Icon aktiv → **Klick** generiert die Verhandlungsnachricht und fügt sie ins Kleinanzeigen-Nachrichtenfeld ein. Voraussetzung: Die Anzeige wurde von Schnappster erfasst (über einen passenden Suchauftrag). Ist sie unbekannt, weist ein Hinweis darauf hin.
- Rückmeldung (Erfolg/Fehler, vorgeschlagenes Gebot) erscheint als kurzer Hinweis auf der Seite.

## Hinweise

- Das Backend muss CORS für die Extension erlauben (im Schnappster-Projekt bereits eingebaut).
- Die Verhandlungsnachricht wird **nie automatisch gesendet** — sie wird nur eingefügt; das Absenden machst du selbst.
