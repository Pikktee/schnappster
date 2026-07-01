"""Rendert den Verhandlungs-Assistent-Prompt aus einer Jinja2-Vorlage."""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader

_PROMPTS_DIR = Path(__file__).resolve().parent


def render_negotiation_prompt(context: dict) -> str:
    """Rendert den Verhandlungs-Prompt (Anweisungen + Anzeigen-Kontext) als kombinierten Text."""
    template = _get_env().get_template("negotiation.jinja2")
    return _strip_leading_whitespace(template.render(**context).strip())


def _strip_leading_whitespace(text: str) -> str:
    """Entfernt führende Leerzeichen pro Zeile für saubere Prompt-Ausgabe."""
    return "\n".join(line.lstrip() for line in text.split("\n"))


def _get_env() -> Environment:
    return Environment(loader=FileSystemLoader(_PROMPTS_DIR), autoescape=False)


__all__ = ["render_negotiation_prompt"]
