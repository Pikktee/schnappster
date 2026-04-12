"""Jinja2-Rendering für eingebettete MCP-App-HTML (ext-apps)."""

from __future__ import annotations

from functools import lru_cache
from importlib.resources import files

from jinja2 import Environment, StrictUndefined

# Gleiche CDN-Zeile wie im offiziellen ext-apps qr-server-Beispiel (stabile 0.4.x).
EXT_APPS_APP_WITH_DEPS = (
    "https://unpkg.com/@modelcontextprotocol/ext-apps@0.4.0/app-with-deps"
)


@lru_cache(maxsize=16)
def _template_source(name: str) -> str:
    return (
        files("schnappster_mcp")
        .joinpath("templates", name)
        .read_text(encoding="utf-8")
    )


def render_mcp_app_html(
    template_name: str,
    *,
    ext_apps_import_url: str | None = None,
) -> str:
    """Lädt ``templates/<template_name>`` und rendert mit Jinja2.

    Autoescape ist aus: fast nur ``<script>``-Inhalt; die CDN-URL ist vertrauenswürdig.
    """
    url = ext_apps_import_url or EXT_APPS_APP_WITH_DEPS
    env = Environment(undefined=StrictUndefined, autoescape=False)
    tpl = env.from_string(_template_source(template_name))
    return tpl.render(ext_apps_import_url=url)
