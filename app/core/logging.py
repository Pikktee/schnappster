"""Logging mit Rich-Handler für die Konsolenausgabe."""

import logging

from rich.logging import RichHandler

RICH_HANDLER = RichHandler(
    show_path=True,
    show_time=True,
    log_time_format="%H:%M:%S",
    markup=False,
    show_level=True,
)


def setup_logging(level: int = logging.INFO) -> None:
    """Anwendungs-Logging einrichten und Rich-Handler an Root- und Uvicorn-Logger hängen."""
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(level)
    root.addHandler(RICH_HANDLER)

    # Uvicorn-Logger ebenfalls im gleichen Format
    uvicorn_loggers = ["uvicorn", "uvicorn.error", "uvicorn.asgi"]
    for logger_name in uvicorn_loggers:
        logger = logging.getLogger(logger_name)
        logger.handlers.clear()
        logger.addHandler(RICH_HANDLER)
        logger.setLevel(level)
        logger.propagate = False

    # Access-Log (jeder GET/POST) und httptools-Ausgaben dämpfen
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

    # „X changes detected“-Meldungen vom Uvicorn-Dateiwächter dämpfen
    logging.getLogger("watchfiles.main").setLevel(logging.WARNING)

    # Ausführliche APScheduler-Job-Registrierungs-Meldungen dämpfen
    logging.getLogger("apscheduler").setLevel(logging.WARNING)

    # Jede httpx-Anfrage (z. B. Supabase GET /auth/v1/user) sonst auf INFO
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    # Auth-/Ads-Stufen (run_sync, inflight): DEBUG wuerde am Root (INFO) verworfen.
    # Eigener Handler + propagate=False wie bei uvicorn — Ausgabe immer sichtbar.
    for trace_name in ("schnappster.auth", "schnappster.ads"):
        trace_log = logging.getLogger(trace_name)
        trace_log.handlers.clear()
        trace_log.setLevel(logging.DEBUG)
        trace_log.addHandler(RICH_HANDLER)
        trace_log.propagate = False
