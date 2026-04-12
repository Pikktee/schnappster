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
