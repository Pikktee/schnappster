"""Schnappster FastAPI application entry point."""

from app.core.bootstrap import create_app

app = create_app()
