"""Rendert Anzeigen-Analyzer-Prompts aus Jinja2-Vorlagen (System + Nutzer)."""

import re
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

_PROMPTS_DIR = Path(__file__).resolve().parent


def render_system_prompt(context: dict | None = None) -> str:
    """Rendert das System-Prompt Template."""
    env = _get_env()
    template = env.get_template("adanalyzer_system.jinja2")
    return _strip_leading_whitespace(template.render(**(context or {})).strip())


def render_user_prompt(context: dict) -> str:
    """Rendert den Nutzer-Nachrichtenteil des Prompts. context kann unvollständig sein."""
    env = _get_env()
    template = env.get_template("adanalyzer_user.jinja2")
    full_context = {**_default_user_context(), **context}
    text = template.render(**full_context).strip()
    text = _strip_leading_whitespace(text)
    return _collapse_blank_lines(text)


def _strip_leading_whitespace(text: str) -> str:
    """Entfernt führende Leerzeichen pro Zeile, damit die Prompt-Ausgabe sauber ist."""
    return "\n".join(line.lstrip() for line in text.split("\n"))


def _collapse_blank_lines(text: str) -> str:
    """Ersetzt 3+ aufeinanderfolgende Zeilenumbrüche durch 2
    (höchstens eine Leerzeile zwischen Blöcken).
    """
    return re.sub(r"\n{3,}", "\n\n", text)


def _get_env() -> Environment:
    return Environment(
        loader=FileSystemLoader(_PROMPTS_DIR),
        autoescape=False,
    )


def _default_user_context() -> dict:
    """Standardwerte für Nutzer-Template-Variablen."""
    return {
        "title": "",
        "price_display": "",
        "description": None,
        "condition": None,
        "shipping_cost": None,
        "location": None,
        "seller_name": None,
        "seller_type": None,
        "seller_rating": None,
        "seller_friendly": False,
        "seller_reliable": False,
        "seller_active_since": None,
        "comparison": None,
        "user_instructions": None,
    }


__all__ = ["render_system_prompt", "render_user_prompt"]
