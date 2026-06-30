"""Rendert Prompts zur KI-Benennung von Preis-Kandidaten aus Jinja2-Vorlagen."""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader

_PROMPTS_DIR = Path(__file__).resolve().parent


def render_pricecandidates_system_prompt() -> str:
    """Rendert das System-Prompt zur Benennung von Preis-Kandidaten."""
    template = _get_env().get_template("pricecandidates_system.jinja2")
    return _strip_leading_whitespace(template.render().strip())


def render_pricecandidates_user_prompt(title: str | None, candidates: list[dict]) -> str:
    """Rendert den Nutzer-Teil mit Titel und nummerierten Kandidaten."""
    template = _get_env().get_template("pricecandidates_user.jinja2")
    text = template.render(title=title or "", candidates=candidates).strip()
    return _strip_leading_whitespace(text)


def _strip_leading_whitespace(text: str) -> str:
    """Entfernt führende Leerzeichen pro Zeile für saubere Prompt-Ausgabe."""
    return "\n".join(line.lstrip() for line in text.split("\n"))


def _get_env() -> Environment:
    return Environment(loader=FileSystemLoader(_PROMPTS_DIR), autoescape=False)


__all__ = ["render_pricecandidates_system_prompt", "render_pricecandidates_user_prompt"]
