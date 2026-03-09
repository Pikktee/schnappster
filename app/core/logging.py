import logging

from rich.logging import RichHandler

RICH_HANDLER = RichHandler(show_path=True, show_time=True, markup=True, show_level=True)


def setup_logging(level: int = logging.INFO) -> None:
    """Configure logging for the application and Uvicorn."""
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(level)
    root.addHandler(RICH_HANDLER)

    # Also configure Uvicorn loggers to use the same format
    uvicorn_loggers = ["uvicorn", "uvicorn.access", "uvicorn.error", "uvicorn.asgi"]
    for logger_name in uvicorn_loggers:
        logger = logging.getLogger(logger_name)
        logger.handlers.clear()
        logger.addHandler(RICH_HANDLER)
        logger.setLevel(level)
        logger.propagate = False

    # Suppress noisy 'X changes detected' messages from Uvicorns file watcher
    logging.getLogger("watchfiles.main").setLevel(logging.WARNING)

    # Suppress verbose APScheduler job registration messages
    logging.getLogger("apscheduler").setLevel(logging.WARNING)
