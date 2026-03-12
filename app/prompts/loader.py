"""Load and render ad-analyzer prompts from Jinja2 template."""

import re
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

_PROMPTS_DIR = Path(__file__).resolve().parent

# Trennlinie für Nutzerinhalt (eindeutig, damit sie in Anzeigentexten praktisch nicht vorkommt)
_USER_DELIMITER = "---SCHNAPPSTER-USER-CONTENT---"

# Im Template steht {{ user_delimiter }} auf einer eigenen Zeile mit Leerzeilen
# → dieses Muster beim Splitten.
_SPLIT_DELIMITER = "\n\n" + _USER_DELIMITER + "\n\n"


def _strip_leading_whitespace(text: str) -> str:
    """Remove leading whitespace from each line so prompt output is clean."""
    return "\n".join(line.lstrip() for line in text.split("\n"))


def _collapse_blank_lines(text: str) -> str:
    """Replace 3+ consecutive newlines with 2 (höchstens eine Leerzeile zwischen Blöcken)."""
    return re.sub(r"\n{3,}", "\n\n", text)


def _get_env() -> Environment:
    return Environment(
        loader=FileSystemLoader(_PROMPTS_DIR),
        autoescape=False,
    )


def _render_full(context: dict) -> str:
    env = _get_env()
    template = env.get_template("adanalyzer.jinja2")
    return template.render(**context).strip()


def _minimal_user_context() -> dict:
    """Context with empty/None user fields for rendering system part only."""
    return {
        "user_delimiter": _USER_DELIMITER,
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


def _get_system_prompt() -> str:
    full = _render_full(_minimal_user_context())
    part1, _sep, _part2 = full.partition(_SPLIT_DELIMITER)
    return _strip_leading_whitespace(part1).strip()


ADANALYZER_PROMPT = _get_system_prompt()


def render_user_content(context: dict) -> str:
    """Render the user-message part of the prompt. context must include all user fields."""
    full_context = {**_minimal_user_context(), **context}
    full = _render_full(full_context)
    _part1, _sep, part2 = full.partition(_SPLIT_DELIMITER)
    if not part2:
        return ""
    text = _strip_leading_whitespace(part2).strip()
    return _collapse_blank_lines(text)


# Für Logs: gleicher Delimiter wie im Template, damit die Grenze System/User sichtbar ist
USER_CONTENT_DELIMITER = _SPLIT_DELIMITER


__all__ = ["ADANALYZER_PROMPT", "render_user_content", "USER_CONTENT_DELIMITER"]
