"""CLI-Übersicht: Alle Schnappster-Befehle und Optionen.

Usage:
    uv run help
"""

from __future__ import annotations

from rich.console import Console
from rich.rule import Rule

console = Console()

_COMMANDS = (
    (
        "start \\[--skip-tests] \\[--dev] \\[--port PORT]",
        "Server starten: Tests, Frontend-Build, FastAPI mit statischem Frontend.",
        (
            ("--skip-tests", "Tests überspringen"),
            ("--dev", "Dev-Modus: Next.js :3000, Backend mit Reload"),
            ("--port PORT", "Port für Backend (Standard: 8000)"),
        ),
    ),
    (
        "scrape \\[adsearch_id]",
        "Scraping manuell auslösen (alle aktiven Suchen oder eine nach ID).",
        (("\\[adsearch_id]", "Optional; sonst alle aktiven AdSearches"),),
    ),
    (
        "analyze \\[limit]",
        "KI-Auswertung für unverarbeitete Anzeigen.",
        (("\\[limit]", "Max. Anzahl (Standard: 10)"),),
    ),
    (
        "dbreset",
        "Datenbank löschen und neu anlegen (Schema nur).",
        (),
    ),
    (
        "seed",
        "Datenbank mit Beispieldaten füllen (alle Tabellen).",
        (),
    ),
    (
        "docs \\[--open]",
        "Dokumentation bauen (pdoc, Architektur, Frontend, Präsentation) nach docs/build/.",
        (("--open, -O", "Nach dem Bau im Browser öffnen"),),
    ),
    (
        "pack-extension \\[--output PFAD]",
        "Chrome-Extension als ZIP für den Web Store packen.",
        (("--output, -o", "Optionaler ZIP-Ausgabepfad"),),
    ),
    (
        "help",
        "Diese Übersicht.",
        (),
    ),
)


def main() -> None:
    """Print CLI command overview (Schnappster commands and options)."""
    console.print()
    console.print("[bold]Schnappster[/bold]  Kleinanzeigen.de Schnäppchen-Finder")
    console.print()
    console.print("[dim]uv run <befehl> [optionen][/dim]")
    console.print()
    console.print(Rule("Befehle", style="dim"))
    console.print()

    for cmd, desc, options in _COMMANDS:
        console.print(f"  [bold cyan]{cmd}[/bold cyan]")
        console.print(f"  [white]{desc}[/white]")
        for opt, opt_desc in options:
            console.print(f"    [dim]{opt}[/dim]  {opt_desc}")
        console.print()
