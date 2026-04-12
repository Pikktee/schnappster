"""Übersicht aller Schnappster-Befehle (wird von ``uv run help`` ausgegeben)."""

from __future__ import annotations

from rich.console import Console
from rich.rule import Rule

console = Console()

_COMMANDS = (
    (
        "start \\[--skip-tests] \\[--prod] \\[--port PORT]",
        "Startet standardmäßig Next.js-Devserver (:3000) und FastAPI (:8000); zuerst laufen die "
        "Tests. Mit --prod nur die API (kein npm run dev).",
        (
            ("--skip-tests", "Tests nicht ausführen"),
            ("--prod", "Nur FastAPI/Uvicorn (kein Next.js-Devserver)"),
            ("--port PORT", "Port nur für die API (Standard: 8000); Next.js bleibt :3000"),
        ),
    ),
    (
        "scrape \\[adsearch_id]",
        "Holt Anzeigen von Kleinanzeigen manuell ab – für alle aktiven Suchaufträge oder nur "
        "für eine Suche (ID).",
        (("\\[adsearch_id]", "Optional: nur diese Suche; sonst alle aktiven"),),
    ),
    (
        "analyze \\[limit]",
        "Bewertet noch nicht ausgewertete Anzeigen mit der KI (Schnäppchen-Score usw.).",
        (("\\[limit]", "Höchstens so viele Anzeigen (Standard: 10)"),),
    ),
    (
        "mcp-server [--http-proxy] [--port PORT] […]  bzw. ohne TTY [--tunnel|-t] …",
        "Startet den Remote-MCP-Server (Projekt mcp-server/, nutzt die .env im Repo-Root). "
        "Im Terminal (TTY): Quick-Tunnel; MCP per ``r`` neu, HTTP-Proxy (mitmdump) per ``p``, "
        "``q`` beenden (Hinweise in der Start-Box). "
        "``--http-proxy``: mitmdump von Anfang an. Ohne TTY: einmaliger Start; ``--tunnel``.",
        (
            ("Standard (TTY)", "TryCloudflare; Tasten ``r`` / ``p`` / ``q``"),
            ("`--tunnel`, `-t`", "Nur ohne TTY: einmaliger Start mit TryCloudflare + MCP"),
            ("`--http-proxy`", "mitmdump; im TTY von Anfang an, sonst impliziert ``--tunnel``"),
            (
                "`--port PORT`, `-p`",
                "Lokaler Port; mit --http-proxy: Proxy auf diesem Port, MCP eine Portnummer höher",
            ),
        ),
    ),
    (
        "dbreset",
        "Löscht die Datenbank und legt sie mit frischem Schema neu an (keine Alembic-Migrationen).",
        (),
    ),
    (
        "seed",
        "Füllt die Datenbank mit Beispieldaten zum Ausprobieren.",
        (),
    ),
    (
        "docs \\[--open]",
        "Baut die Projektdokumentation (pdoc usw.) nach docs/build/.",
        (("--open, -O", "Nach dem Bau im Browser öffnen"),),
    ),
    (
        "release \\[major|minor|patch]",
        "Erhöht die Versionsnummer, commitet, pusht und erstellt einen Git-Tag.",
        (("\\[major|minor|patch]", "Art des Versionssprungs (Standard: patch)"),),
    ),
    (
        "release-chrome-extension \\[patch|minor|major] \\[--output-dir PFAD] \\[--output PFAD]",
        "Packt die Chrome-Erweiterung als ZIP und erhöht die Version im Manifest.",
        (
            ("\\[patch|minor|major]", "Welche Stelle der Version erhöht wird (Standard: patch)"),
            ("--output-dir, -d", "Zielordner (Standard: extensions/dist)"),
            ("--output, -o", "Fester ZIP-Pfad (ersetzt --output-dir)"),
        ),
    ),
    (
        "help",
        "Zeigt diese Befehlsübersicht.",
        (),
    ),
)


def main() -> None:
    """Gibt die Schnappster-CLI-Hilfe auf stdout aus."""
    console.print()
    console.print("[bold]Schnappster[/bold]  Schnäppchen-Finder für Kleinanzeigen")
    console.print()
    console.print("[dim]Aufruf:  uv run <befehl>  … optional weitere Argumente[/dim]")
    console.print()
    console.print(Rule("Befehle", style="dim"))
    console.print()

    for cmd, desc, options in _COMMANDS:
        console.print(f"  [bold cyan]{cmd}[/bold cyan]")
        console.print(f"  [white]{desc}[/white]")
        for opt, opt_desc in options:
            console.print(f"    [dim]{opt}[/dim]  {opt_desc}")
        console.print()
